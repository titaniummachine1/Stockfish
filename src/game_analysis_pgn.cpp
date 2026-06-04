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

Move san_to_move(const Position& pos, std::string san) {
    san = normalize_san(std::move(san));

    for (const auto& m : MoveList<LEGAL>(pos))
        if (normalize_san(move_to_san(pos, m)) == san)
            return m;

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
