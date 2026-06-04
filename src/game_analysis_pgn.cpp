/*
  Stockfish, a UCI chess playing engine derived from Glaurung 2.1
  Copyright (C) 2004-2026 The Stockfish developers (see AUTHORS file)

  Stockfish is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Stockfish is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "game_analysis_pgn.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <map>
#include <sstream>

#include "movegen.h"
#include "position.h"
#include "uci.h"

namespace Stockfish::GameAnalysis {

namespace {

std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace(unsigned(s[a])))
        ++a;
    while (b > a && std::isspace(unsigned(s[b - 1])))
        --b;
    return s.substr(a, b - a);
}

std::string to_upper_copy(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return char(std::toupper(c)); });
    return s;
}

bool ends_with_ci(const std::string& path, const std::string& ext) {
    if (path.size() < ext.size())
        return false;
    return std::equal(ext.rbegin(), ext.rend(), path.rbegin(),
                      [](char a, char b) {
                          return std::tolower(unsigned(a)) == std::tolower(unsigned(b));
                      });
}

char piece_type_char(Piece pc) {
    switch (type_of(pc))
    {
    case KNIGHT :
        return 'N';
    case BISHOP :
        return 'B';
    case ROOK :
        return 'R';
    case QUEEN :
        return 'Q';
    case KING :
        return 'K';
    default :
        return '?';
    }
}

std::string normalize_san(std::string san) {
    san = trim(san);
    std::replace(san.begin(), san.end(), '0', 'O');

    while (!san.empty())
    {
        char c = san.back();
        if (c == '+' || c == '#' || c == '!' || c == '?')
            san.pop_back();
        else
            break;
    }

    return san;
}

bool is_result_token(const std::string& t) {
    return t == "1-0" || t == "0-1" || t == "1/2-1/2" || t == "*" || t == "1/2-1/2-1/2";
}

bool is_move_number_token(const std::string& t) {
    if (t.empty())
        return false;
    size_t i = 0;
    while (i < t.size() && std::isdigit(unsigned(t[i])))
        ++i;
    return i > 0 && i < t.size() && t[i] == '.';
}

std::string strip_pgn_comments_and_variations(std::string s) {
    std::string out;
    out.reserve(s.size());
    int depthBrace = 0, depthParen = 0;
    for (size_t i = 0; i < s.size(); ++i)
    {
        char c = s[i];
        if (c == '{' && depthParen == 0)
        {
            ++depthBrace;
            continue;
        }
        if (c == '}' && depthBrace > 0)
        {
            --depthBrace;
            continue;
        }
        if (c == '(' && depthBrace == 0)
        {
            ++depthParen;
            continue;
        }
        if (c == ')' && depthParen > 0)
        {
            --depthParen;
            continue;
        }
        if (depthBrace == 0 && depthParen == 0)
            out.push_back(c);
    }
    return out;
}

std::string move_to_san(const Position& pos, Move m) {
    const bool chess960 = pos.is_chess960();

    if (m.type_of() == CASTLING)
    {
        if (chess960)
            return file_of(m.to_sq()) > file_of(m.from_sq()) ? "O-O" : "O-O-O";
        return file_of(m.to_sq()) == FILE_G ? "O-O" : "O-O-O";
    }

    const Square from = m.from_sq();
    const Square to   = m.to_sq();
    const Piece  pc   = pos.moved_piece(m);

    if (type_of(pc) == PAWN)
    {
        std::string san;
        if (pos.capture(m))
            san += char('a' + file_of(from));
        if (pos.capture(m) || m.type_of() == EN_PASSANT)
            san += 'x';
        san += UCIEngine::square(to);
        if (m.type_of() == PROMOTION)
            san += std::string("=") + piece_type_char(make_piece(WHITE, m.promotion_type()));
        return san;
    }

    std::string san;
    san += piece_type_char(pc);

    MoveList<LEGAL> ml(pos);
    int same = 0;
    for (const auto& cand : ml)
    {
        if (cand == m)
            continue;
        if (pos.moved_piece(cand) == pc && cand.to_sq() == to)
            ++same;
    }

    if (same > 0)
    {
        bool needFile = false, needRank = false;
        for (const auto& cand : ml)
        {
            if (cand == m)
                continue;
            if (pos.moved_piece(cand) != pc || cand.to_sq() != to)
                continue;
            if (file_of(cand.from_sq()) == file_of(from))
                needRank = true;
            if (rank_of(cand.from_sq()) == rank_of(from))
                needFile = true;
        }
        if (needFile)
            san += char('a' + file_of(from));
        if (needRank)
            san += char('1' + rank_of(from));
    }

    if (pos.capture(m))
        san += 'x';
    san += UCIEngine::square(to);
    if (m.type_of() == PROMOTION)
        san += std::string("=") + piece_type_char(make_piece(WHITE, m.promotion_type()));

    return san;
}

struct SanParts {
    PieceType pt       = NO_PIECE_TYPE;
    Square    to       = SQ_NONE;
    File      disFile  = FILE_NB;
    Rank      disRank  = RANK_NB;
};

PieceType piece_type_from_char(char c) {
    switch (c)
    {
    case 'N' :
        return KNIGHT;
    case 'B' :
        return BISHOP;
    case 'R' :
        return ROOK;
    case 'Q' :
        return QUEEN;
    case 'K' :
        return KING;
    default :
        return NO_PIECE_TYPE;
    }
}

Square square_from_chars(char f, char r) {
    if (f < 'a' || f > 'h' || r < '1' || r > '8')
        return SQ_NONE;
    return make_square(File(f - 'a'), Rank(r - '1'));
}

bool parse_piece_san(const std::string& san, SanParts& sp) {
    const PieceType pt = piece_type_from_char(san[0]);
    if (pt == NO_PIECE_TYPE)
        return false;

    size_t end = san.size();
    if (end >= 3 && san[end - 2] == '=')
        end -= 2;
    if (end < 3)
        return false;

    sp.pt = pt;
    sp.to = square_from_chars(san[end - 2], san[end - 1]);
    if (sp.to == SQ_NONE)
        return false;

    size_t j = 1;
    if (j < end - 2 && san[j] == 'x')
        ++j;
    if (j < end - 2 && san[j] >= 'a' && san[j] <= 'h')
        sp.disFile = File(san[j++] - 'a');
    if (j < end - 2 && san[j] >= '1' && san[j] <= '8')
        sp.disRank = Rank(san[j++] - '1');
    if (j < end - 2 && san[j] == 'x')
        ++j;
    return j == end - 2;
}

bool parse_pawn_san(const std::string& san, SanParts& sp) {
    if (san.empty() || san[0] < 'a' || san[0] > 'h')
        return false;

    size_t end = san.size();
    if (end >= 3 && san[end - 2] == '=')
        end -= 2;
    if (end < 2)
        return false;

    const size_t destOff = end - 2;
    sp.pt                = PAWN;
    sp.to                = square_from_chars(san[destOff], san[destOff + 1]);
    if (sp.to == SQ_NONE)
        return false;

    if (end == 2)
        return san[1] >= '1' && san[1] <= '8';

    return san[1] == 'x' && destOff >= 2;
}

Move match_san_parts(const Position& pos, const SanParts& sp) {
    for (const auto& m : MoveList<LEGAL>(pos))
    {
        if (type_of(pos.moved_piece(m)) != sp.pt)
            continue;
        if (m.to_sq() != sp.to)
            continue;
        if (sp.disFile != FILE_NB && file_of(m.from_sq()) != sp.disFile)
            continue;
        if (sp.disRank != RANK_NB && rank_of(m.from_sq()) != sp.disRank)
            continue;
        return m;
    }
    return Move::none();
}

Move san_to_move(const Position& pos, std::string san) {
    san = normalize_san(std::move(san));

    if (san == "O-O" || san == "O-O-O")
    {
        const bool     kingside = (san == "O-O");
        const Color    us       = pos.side_to_move();
        const Square   ksq      = pos.square<KING>(us);
        const File     kfile    = kingside ? FILE_G : FILE_C;
        const std::string uci =
          UCIEngine::square(ksq) + UCIEngine::square(make_square(kfile, rank_of(ksq)));
        const Move m = UCIEngine::to_move(pos, uci);
        if (m != Move::none())
            return m;

        for (const auto& cand : MoveList<LEGAL>(pos))
            if (cand.type_of() == CASTLING)
            {
                if (pos.is_chess960())
                {
                    if (kingside == (file_of(cand.to_sq()) > file_of(cand.from_sq())))
                        return cand;
                }
                else if (kingside && file_of(cand.to_sq()) == FILE_G)
                    return cand;
                else if (!kingside && file_of(cand.to_sq()) == FILE_C)
                    return cand;
            }
        return Move::none();
    }

    for (const auto& m : MoveList<LEGAL>(pos))
        if (normalize_san(move_to_san(pos, m)) == san)
            return m;

    SanParts sp;
    if (parse_piece_san(san, sp) || parse_pawn_san(san, sp))
    {
        const Move m = match_san_parts(pos, sp);
        if (m != Move::none())
            return m;
    }

    return Move::none();
}

std::vector<std::string> tokenize_movetext(std::string text) {
    text = strip_pgn_comments_and_variations(std::move(text));
    std::istringstream is(text);
    std::vector<std::string> moves;
    std::string              tok;
    while (is >> tok)
    {
        if (is_move_number_token(tok) || is_result_token(tok))
            continue;
        if (tok.size() >= 2 && tok[0] == '$' && std::isdigit(unsigned(tok[1])))
            continue;
        moves.push_back(tok);
    }
    return moves;
}

std::optional<std::string>
convert_sans_to_uci(const std::string& fen, bool chess960, const std::vector<std::string>& sans,
                    std::vector<std::string>& uciOut) {
    StateListPtr states(new std::deque<StateInfo>(1));
    Position     pos;
    if (auto err = pos.set(fen, chess960, &states->back()))
        return err->what();

    uciOut.clear();
    for (const std::string& san : sans)
    {
        const Move m = san_to_move(pos, san);
        if (m == Move::none())
            return "illegal or unrecognized SAN: " + san;

        uciOut.push_back(UCIEngine::move(m, chess960));
        states->emplace_back();
        pos.do_move(m, states->back());
    }
    return std::nullopt;
}

bool chess960_from_headers(const std::map<std::string, std::string>& headers) {
    auto it = headers.find("Variant");
    if (it != headers.end())
    {
        const std::string v = to_upper_copy(it->second);
        if (v.find("CHESS960") != std::string::npos || v.find("FISCHER") != std::string::npos)
            return true;
    }
    it = headers.find("UCI_Variant");
    if (it != headers.end() && to_upper_copy(it->second) == "CHESS960")
        return true;
    return false;
}

std::string fen_from_headers(const std::map<std::string, std::string>& headers) {
    auto it = headers.find("FEN");
    if (it != headers.end() && !it->second.empty())
        return it->second;
    return StartFEN;
}

struct RawPgnGame {
    std::map<std::string, std::string> headers;
    std::string                        movetext;
};

std::vector<RawPgnGame> parse_pgn_stream(std::istream& in, std::string& error) {
    std::vector<RawPgnGame> games;
    RawPgnGame              current;
    bool                    inHeaders  = false;
    bool                    inMovetext = false;
    std::string             line;

    auto flush_game = [&]() {
        if (!current.headers.empty() || !trim(current.movetext).empty())
            games.push_back(std::move(current));
        current = RawPgnGame{};
        inHeaders = inMovetext = false;
    };

    while (std::getline(in, line))
    {
        line = trim(line);
        if (line.empty())
        {
            if (inMovetext)
                flush_game();
            continue;
        }

        if (line[0] == '[')
        {
            if (inMovetext)
                flush_game();
            inHeaders  = true;
            inMovetext = false;

            const size_t nameEnd = line.find(' ');
            const size_t valStart  = line.find('"');
            const size_t valEnd    = line.rfind('"');
            if (nameEnd == std::string::npos || valStart == std::string::npos
                || valEnd <= valStart)
            {
                error = "malformed PGN header: " + line;
                return {};
            }
            std::string name = line.substr(1, nameEnd - 1);
            std::string val  = line.substr(valStart + 1, valEnd - valStart - 1);
            current.headers[name] = val;
            continue;
        }

        inHeaders  = false;
        inMovetext = true;
        if (!current.movetext.empty())
            current.movetext += ' ';
        current.movetext += line;
    }

    if (inMovetext || !current.headers.empty())
        flush_game();

    if (games.empty())
        error = "no games in PGN";

    return games;
}

}  // namespace

bool is_pgn_path(const std::string& path) {
    return ends_with_ci(path, ".pgn");
}

std::optional<std::string> san_movetext_to_uci(const std::string& fen, bool chess960,
                                               const std::vector<std::string>& sans,
                                               std::vector<std::string>& uciOut) {
    return convert_sans_to_uci(fen, chess960, sans, uciOut);
}

std::vector<GameSpec> load_games_from_pgn(const std::string& path, std::string& error) {
    std::ifstream f(path);
    if (!f)
    {
        error = "cannot open PGN: " + path;
        return {};
    }

    auto raw = parse_pgn_stream(f, error);
    if (!error.empty())
        return {};

    std::vector<GameSpec> games;
    games.reserve(raw.size());

    for (size_t gi = 0; gi < raw.size(); ++gi)
    {
        const auto& rg = raw[gi];
        GameSpec    game;
        game.fen       = fen_from_headers(rg.headers);
        const bool c960 = chess960_from_headers(rg.headers);

        auto sans = tokenize_movetext(rg.movetext);
        if (auto convErr = convert_sans_to_uci(game.fen, c960, sans, game.moves))
        {
            error = "PGN game " + std::to_string(gi + 1) + ": " + *convErr;
            return {};
        }

        games.push_back(std::move(game));
    }

    return games;
}

}  // namespace Stockfish::GameAnalysis
