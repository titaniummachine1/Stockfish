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

#include "game_analysis.h"
#include "game_analysis_pgn.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <map>
#include <sstream>

#include "engine.h"
#include "misc.h"
#include "numa.h"
#include "score.h"
#include "search.h"
#include "uci.h"

namespace Stockfish::GameAnalysis {

namespace {

constexpr int MateScoreCp = 30000;

int effective_threads(int threadsOpt) {
    if (threadsOpt > 0)
        return threadsOpt;
    return std::max(1, int(get_hardware_concurrency()));
}

void apply_engine_options(Engine& engine, const Options& opts) {
    const int threads = effective_threads(opts.threads);
    {
        std::istringstream tIs("name Threads value " + std::to_string(threads));
        engine.get_options().setoption(tIs);
    }
    // Larger TT helps multi-thread spine walks reuse prior plies' subtrees.
    if (threads >= 2)
    {
        const int hashMb = std::min(4096, threads * threads * 16);
        std::istringstream hIs("name Hash value " + std::to_string(hashMb));
        engine.get_options().setoption(hIs);
    }
    {
        std::istringstream mpvIs("name MultiPV value " + std::to_string(opts.multiPv));
        engine.get_options().setoption(mpvIs);
    }
}

void print(const PrintFn& out, const std::string& line) {
    if (out)
        out(line);
}

int score_to_cp(const Score& s) {
    if (s.is<Score::InternalUnits>())
        return s.get<Score::InternalUnits>().value;
    return s.is<Score::Mate>() ? (s.get<Score::Mate>().plies > 0 ? MateScoreCp : -MateScoreCp)
                               : 0;
}

std::string first_token_of_pv(std::string_view pv) {
    std::string s(pv);
    auto        pos = s.find(' ');
    if (pos != std::string::npos)
        s.resize(pos);
    return UCIEngine::to_lower(s);
}

struct PlyAccumulator {
    int                   bestDepth = 0;
    std::map<int, PvLine> snapshotByMp;
    uint64_t              nodes    = 0;
    uint64_t              timeMs   = 0;
    int                   hashfull = 0;

    void update(const Engine::InfoFull& info) {
        nodes    = info.nodes;
        timeMs   = info.timeMs;
        hashfull = info.hashfull;

        if (info.depth > bestDepth)
        {
            bestDepth = info.depth;
            snapshotByMp.clear();
        }

        if (info.depth != bestDepth)
            return;

        PvLine line;
        line.multipv    = int(info.multiPV);
        line.depth      = info.depth;
        line.scoreText  = UCIEngine::format_score(info.score);
        line.scoreCp    = score_to_cp(info.score);
        line.isMate     = info.score.is<Score::Mate>();
        line.pv         = std::string(info.pv);
        line.pvFirstUci = first_token_of_pv(info.pv);
        snapshotByMp[line.multipv] = std::move(line);
    }

    PlyResult freeze(int gamePly, const std::string& fen) const {
        PlyResult r;
        r.gamePly   = gamePly;
        r.fen       = fen;
        r.bestDepth = bestDepth;
        r.nodes     = nodes;
        r.timeMs    = timeMs;
        r.hashfull  = hashfull;
        for (const auto& [_, line] : snapshotByMp)
            r.lines.push_back(line);
        std::sort(r.lines.begin(), r.lines.end(),
                  [](const PvLine& a, const PvLine& b) { return a.multipv < b.multipv; });
        return r;
    }
};

void emit_final(const PlyResult& ply, const PrintFn& out) {
    for (const auto& line : ply.lines)
    {
        std::ostringstream ss;
        ss << "gameanalysis final gameply " << ply.gamePly << " depth " << ply.bestDepth
           << " multipv " << line.multipv << " score " << line.scoreText << " nodes " << ply.nodes
           << " nps " << (ply.timeMs ? ply.nodes * 1000 / ply.timeMs : 0) << " hashfull "
           << ply.hashfull << " pv " << line.pv;
        print(out, ss.str());
    }
}

void emit_live(int gamePly, const Engine::InfoFull& info, const PrintFn& out) {
    std::ostringstream ss;
    ss << "gameanalysis live gameply " << gamePly << " depth " << info.depth << " multipv "
       << info.multiPV << " score " << UCIEngine::format_score(info.score) << " nodes " << info.nodes
       << " pv " << info.pv;
    print(out, ss.str());
}

int find_played_rank(const PlyResult& parent, const std::string& playedUci) {
    const std::string played = UCIEngine::to_lower(playedUci);
    for (const auto& line : parent.lines)
        if (line.pvFirstUci == played)
            return line.multipv;
    return -1;
}

int line_cp_for_move(const PlyResult& parent, const std::string& playedUci) {
    const std::string played = UCIEngine::to_lower(playedUci);
    for (const auto& line : parent.lines)
        if (line.pvFirstUci == played)
            return line.scoreCp;
    return 0;
}

int best_line_cp(const PlyResult& parent) {
    for (const auto& line : parent.lines)
        if (line.multipv == 1)
            return line.scoreCp;
    return parent.lines.empty() ? 0 : parent.lines.front().scoreCp;
}

int played_move_cpl(const PlyResult& parent, const std::string& playedUci) {
    const int rank = find_played_rank(parent, playedUci);
    if (parent.lines.empty())
        return 0;
    const int bestCp = best_line_cp(parent);
    if (rank > 0)
        return std::max(0, bestCp - line_cp_for_move(parent, playedUci));
    return bestCp;
}

struct SpineStep {
    int  startDepth = 1;
    bool continueTt = true;
};

int apply_resume_horizon_cap(int startDepth, int prev, int target, int horizon) {
    const int h          = std::max(1, horizon);
    const int maxStart   = std::max(1, std::min({prev, target}) - h + 1);
    return std::min(startDepth, maxStart);
}

// TT depth d means ply d was stored; next ID rung to search is d+1 (capped at target).
int start_depth_after_tt(int ttDepth, int target) {
    if (ttDepth <= 0)
        return 0;
    if (ttDepth >= target)
        return target;
    return std::min(target, ttDepth + 1);
}

int cap_start_with_tt(int start, int ttDepth, int target) {
    if (start <= 1)
        return 1;
    const int afterTt = start_depth_after_tt(ttDepth, target);
    if (afterTt <= 0)
        return 1;
    return std::min(start, afterTt);
}

SpineStep compute_spine_step(const Options& opts, const PlyResult& parent,
                             const std::string& enteredViaUci, int ttDepthAtRoot) {
    SpineStep step;
    if (opts.resume == 0 || opts.cold != 0)
        return step;

    const int prev   = parent.bestDepth;
    const int target = opts.depth;
    if (prev <= 1)
        return step;

    const int rank = find_played_rank(parent, enteredViaUci);
    const int cpl  = played_move_cpl(parent, enteredViaUci);

    if (opts.resume == 1)
        step.startDepth = std::max(1, std::min(prev, target) - 1);
    else if (rank == 1 && cpl <= 120)
        step.startDepth = std::max(1, std::min(prev, target));
    else if (rank > 1 && rank <= opts.multiPv && cpl <= 80)
        step.startDepth = std::max(1, std::min(prev - 1, target));
    else
    {
        step.startDepth = 1;
        step.continueTt = false;
    }

    if (opts.resume >= 3 && step.continueTt)
    {
        const int evidence = std::max(prev, ttDepthAtRoot);
        const int afterTt  = start_depth_after_tt(ttDepthAtRoot, target);
        if (afterTt > 0)
            step.startDepth = std::max(step.startDepth, afterTt);
        step.startDepth =
          apply_resume_horizon_cap(step.startDepth, evidence, target, opts.resumeHorizon);
    }
    else
        step.startDepth =
          apply_resume_horizon_cap(step.startDepth, prev, target, opts.resumeHorizon);

    step.startDepth = cap_start_with_tt(step.startDepth, ttDepthAtRoot, target);

    // Depth-D eval must come from a full iterative deepening chain 1..D (same as naive go depth D).
    if (opts.strict)
        step.startDepth = 1;

    return step;
}

int consolidate_start_depth(int targetDepth, int completedDepth, int ttDepth) {
    if (ttDepth < targetDepth - 1)
        return 0;
    if (completedDepth >= targetDepth)
        return targetDepth;
    const int afterTt = start_depth_after_tt(ttDepth, targetDepth);
    return afterTt > 0 ? afterTt : 1;
}

std::vector<std::string> parent_pv_suffix(const PlyResult& parent, const std::string& via) {
    const std::string played = UCIEngine::to_lower(via);
    for (const auto& line : parent.lines)
    {
        if (line.pvFirstUci != played)
            continue;
        std::vector<std::string> suffix;
        std::istringstream       is(line.pv);
        std::string              tok;
        if (is >> tok)
            while (is >> tok)
                suffix.push_back(UCIEngine::to_lower(tok));
        return suffix;
    }
    return {};
}

std::optional<std::string> search_spine_ply(Engine& engine, const Options& opts, int gamePly,
                                            const GameSpec& game,
                                            const std::vector<std::string>& prefix,
                                            Search::LimitsType limits, PlyResult& out,
                                            const PrintFn& printOut, bool positionReady) {
    engine.wait_for_search_finished();

    if (!positionReady)
        if (auto err = engine.set_position(game.fen, prefix))
            return err->what();

    PlyAccumulator acc;

    engine.set_on_update_no_moves([](const Engine::InfoShort&) {});
    engine.set_on_iter([](const Engine::InfoIter&) {});
    engine.set_on_update_full([&](const Engine::InfoFull& info) {
        acc.update(info);
        if (opts.live)
            emit_live(gamePly, info, printOut);
    });

    bool searchDone = false;
    engine.set_on_bestmove([&](std::string_view, std::string_view) { searchDone = true; });

    limits.depth     = opts.depth;
    limits.startTime = now();
    engine.go(limits);
    engine.wait_for_search_finished();

    if (!searchDone)
        return "search did not complete";

    out = acc.freeze(gamePly, engine.fen());
    return std::nullopt;
}

void emit_grade(int moveNumber, const std::string& playedUci, const PlyResult& parent,
                const PrintFn& out) {
    const int rank = find_played_rank(parent, playedUci);
    int       cpl  = 0;
    if (!parent.lines.empty())
    {
        const int bestCp = best_line_cp(parent);
        if (rank > 0)
            cpl = bestCp - line_cp_for_move(parent, playedUci);
        else
            cpl = bestCp;
    }

    std::ostringstream ss;
    ss << "gameanalysis grade move " << moveNumber << " played " << playedUci << " rank " << rank
       << " cpl " << cpl;
    print(out, ss.str());
}

std::optional<std::string> run_single_game(Engine& engine, const Options& opts, const GameSpec& game,
                                           const PrintFn& out) {
    if (opts.depth <= 0)
        return "depth must be positive";

    if (int(game.moves.size()) + 1 > opts.maxPlies)
        return "move count exceeds maxplies limit";

    if (opts.cold == 2)
        return "cold 2 not implemented";

    // Strict parity: full 1..D ladder, no resume shortcuts (same search path as resume 0).
    const bool useResume = opts.resume && opts.cold == 0 && !opts.strict;

    engine.wait_for_search_finished();

    // set_position rebuilds StateInfo only; histories/TT persist unless search_clear().
    if (opts.cold == 1)
        engine.search_clear();

    apply_engine_options(engine, opts);

    {
        std::ostringstream ss;
        ss << "gameanalysis threads " << effective_threads(opts.threads);
        print(out, ss.str());
    }

    Report                   report;
    std::vector<std::string> prefix;
    std::optional<PlyResult>   previousPly;

    const int spinePlies = std::min(int(game.moves.size()) + 1, opts.maxPlies);

    uint64_t consolidateNodes = 0;
    bool     allSpineAtDepth  = true;
    int      maxSpineStartDepth = 1;

    for (int gamePly = 0; gamePly < spinePlies; ++gamePly)
    {
        Search::LimitsType limits;
        limits.startTime         = now();
        limits.spineContinueTt  = opts.cold == 0 && gamePly > 0;
        limits.spineStrictParity = opts.strict != 0;

        engine.wait_for_search_finished();
        if (auto err = engine.set_position(game.fen, prefix))
            return err->what();

        const int ttDepthAtRoot =
          (opts.cold == 0 && gamePly > 0) ? engine.spine_tt_depth() : 0;

        if (useResume && previousPly && gamePly > 0)
        {
            const std::string& via  = game.moves[gamePly - 1];
            const SpineStep    step = compute_spine_step(opts, *previousPly, via, ttDepthAtRoot);
            limits.startDepth       = step.startDepth;
            if (!step.continueTt)
                limits.spineContinueTt = false;
            if (limits.startDepth > 1)
                limits.spineTtMinDepth = limits.startDepth;
            if (opts.resume >= 2 && !opts.strict)
                limits.spinePvOrder = parent_pv_suffix(*previousPly, via);
            if (limits.startDepth > 1)
            {
                std::ostringstream rs;
                rs << "gameanalysis resume gameply " << gamePly << " startdepth "
                   << limits.startDepth << " ttdepth " << ttDepthAtRoot << " rank "
                   << find_played_rank(*previousPly, via) << " cpl "
                   << played_move_cpl(*previousPly, via);
                print(out, rs.str());
            }
        }

        maxSpineStartDepth = std::max(maxSpineStartDepth, std::max(1, limits.startDepth));

        PlyResult ply;
        if (auto err =
              search_spine_ply(engine, opts, gamePly, game, prefix, limits, ply, out, true))
            return err;

        emit_final(ply, out);

        if (previousPly && gamePly > 0)
            emit_grade(gamePly, game.moves[gamePly - 1], *previousPly, out);

        report.totalNodes += ply.nodes;
        report.totalTimeMs += ply.timeMs;
        report.lastHashfull = ply.hashfull;
        report.plies.push_back(std::move(ply));
        previousPly = report.plies.back();
        if (previousPly->bestDepth < opts.depth)
            allSpineAtDepth = false;

        if (gamePly < int(game.moves.size()))
            prefix.push_back(game.moves[gamePly]);
    }

    if (opts.refine && opts.cold == 0 && opts.depth > 1 && !allSpineAtDepth)
    {
        prefix.clear();
        if (spinePlies > 1)
            prefix.assign(game.moves.begin(), game.moves.begin() + spinePlies - 1);

        for (int gamePly = spinePlies - 1; gamePly >= 0; --gamePly)
        {
            engine.wait_for_search_finished();
            if (auto err = engine.set_position(game.fen, prefix))
                return err->what();

            const int ttDepth = engine.spine_tt_depth();
            const int have    = report.plies[gamePly].bestDepth;

            int start = 1;
            if (opts.strict)
            {
                if (have >= opts.depth)
                {
                    if (!prefix.empty())
                        prefix.pop_back();
                    continue;
                }
            }
            else
            {
                start                 = consolidate_start_depth(opts.depth, have, ttDepth);
                const bool freeRefine = have >= opts.depth && ttDepth >= opts.depth - 1;
                if (start <= 0 || (start <= have && !freeRefine))
                {
                    if (!prefix.empty())
                        prefix.pop_back();
                    continue;
                }
            }

            Search::LimitsType limits;
            limits.startTime          = now();
            limits.depth              = opts.depth;
            limits.startDepth         = start;
            limits.spineContinueTt    = true;
            limits.spineTtMinDepth    = 0;
            limits.spineStrictParity  = opts.strict != 0;

            PlyResult ply;
            if (auto serr =
                  search_spine_ply(engine, opts, gamePly, game, prefix, limits, ply, out, true))
                return serr;

            consolidateNodes += ply.nodes;

            std::ostringstream ds;
            ds << "gameanalysis deepen gameply " << gamePly << " ttdepth " << ttDepth
               << " startdepth " << start << " nodes " << ply.nodes;
            print(out, ds.str());

            emit_final(ply, out);
            report.totalNodes += ply.nodes;
            report.totalTimeMs += ply.timeMs;
            report.plies[gamePly] = std::move(ply);

            if (!prefix.empty())
                prefix.pop_back();
        }
    }

    const char* mode = opts.strict ? "parity" : (opts.resume == 0 ? "full" : "resume");

    std::ostringstream ss;
    ss << "gameanalysis summary plies " << report.plies.size() << " nodes " << report.totalNodes
       << " time " << report.totalTimeMs << " hashfull " << report.lastHashfull << " threads "
       << effective_threads(opts.threads) << " mode " << mode << " startdepth "
       << maxSpineStartDepth;
    if (consolidateNodes > 0)
        ss << " deepen_nodes " << consolidateNodes;
    print(out, ss.str());

    return std::nullopt;
}

std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace(unsigned(s[a])))
        ++a;
    while (b > a && std::isspace(unsigned(s[b - 1])))
        --b;
    return s.substr(a, b - a);
}

bool parse_fen_moves_line(const std::string& line, GameSpec& game) {
    std::istringstream is(line);
    std::vector<std::string> tok;
    std::string              t;
    while (is >> t)
        tok.push_back(t);
    if (tok.size() < 6)
        return false;
    game.fen = tok[0] + " " + tok[1] + " " + tok[2] + " " + tok[3] + " " + tok[4] + " " + tok[5];
    size_t moveStart = 6;
    if (tok.size() > 6 && tok[6] == "moves")
        moveStart = 7;
    game.moves.assign(tok.begin() + moveStart, tok.end());
    return true;
}

bool is_move_list_keyword(const std::string& t) {
    return t == "multipv" || t == "live" || t == "cold" || t == "maxplies" || t == "depth"
        || t == "resume" || t == "resumehorizon" || t == "refine" || t == "strict" || t == "threads"
        || t == "file"
        || t == "pgn" || t == "fen" || t == "startpos";
}

bool parse_inline_option(const std::string& token, std::istream& is, Options& opts) {
    if (token == "multipv")
        is >> opts.multiPv;
    else if (token == "live")
        is >> opts.live;
    else if (token == "cold")
        is >> opts.cold;
    else if (token == "maxplies")
        is >> opts.maxPlies;
    else if (token == "resume")
        is >> opts.resume;
    else if (token == "resumehorizon")
        is >> opts.resumeHorizon;
    else if (token == "refine")
        is >> opts.refine;
    else if (token == "strict")
        is >> opts.strict;
    else if (token == "threads")
        is >> opts.threads;
    else
        return false;
    return true;
}

void append_move_token(const std::string& token, std::istream& is, Options& opts) {
    if (parse_inline_option(token, is, opts))
        return;
    if (!is_move_list_keyword(token))
        opts.moves.push_back(token);
}

}  // namespace

std::optional<std::string> parse_options(std::istream& is, Options& opts) {
    std::string token;
    bool        haveDepth = false;

    while (is >> token)
    {
        if (token == "depth")
        {
            is >> opts.depth;
            haveDepth = true;
        }
        else if (parse_inline_option(token, is, opts))
            continue;
        else if (token == "startpos")
        {
            opts.fen = StartFEN;
            std::string next;
            if (is >> next)
            {
                if (next != "moves")
                    return "expected 'moves' after startpos, got: " + next;
                while (is >> next)
                    append_move_token(next, is, opts);
            }
        }
        else if (token == "fen")
        {
            opts.moves.clear();
            opts.fen.clear();
            std::string fenToken;
            while (is >> fenToken && fenToken != "moves")
                opts.fen += fenToken + " ";
            if (!opts.fen.empty())
                opts.fen.pop_back();
            if (fenToken == "moves")
                while (is >> fenToken)
                    append_move_token(fenToken, is, opts);
        }
        else if (token == "file" || token == "pgn")
        {
            std::string path;
            is >> path;
            opts.filePath = path;
        }
        else if (token == "moves")
        {
            while (is >> token)
                append_move_token(token, is, opts);
        }
        else
            return "unknown token: " + token;
    }

    if (!haveDepth)
        return "depth required";

    if (opts.multiPv < 1)
        return "multipv must be >= 1";

    if (opts.maxPlies < 1)
        return "maxplies must be >= 1";

    if (opts.threads < 0)
        return "threads must be >= 0 (0 = all CPUs)";

    if (opts.resume < 0 || opts.resume > 3)
        return "resume must be 0, 1, 2, or 3 (3=merge)";

    if (opts.resumeHorizon < 1 || opts.resumeHorizon > 8)
        return "resumehorizon must be 1..8";

    if (opts.refine < 0 || opts.refine > 1)
        return "refine must be 0 or 1";

    if (opts.strict < 0 || opts.strict > 1)
        return "strict must be 0 or 1";

    return std::nullopt;
}

std::vector<GameSpec> load_games_from_file(const std::string& path, std::string& error) {
    if (is_pgn_path(path))
        return load_games_from_pgn(path, error);

    std::ifstream f(path);
    if (!f)
    {
        error = "cannot open file: " + path;
        return {};
    }

    std::vector<GameSpec> games;
    std::string             line;
    while (std::getline(f, line))
    {
        line = trim(line);
        if (line.empty() || line[0] == '#')
            continue;
        GameSpec game;
        if (!parse_fen_moves_line(line, game))
        {
            error = "invalid game line: " + line;
            return {};
        }
        games.push_back(std::move(game));
    }

    if (games.empty())
        error = "no games in file";

    return games;
}

std::optional<std::string> run(Engine& engine, const Options& opts, PrintFn printFn) {
    auto emit = [&](std::string_view msg) {
        sync_cout_start();
        std::cout << "info string " << msg << '\n';
        sync_cout_end();
        if (printFn)
            printFn(msg);
    };
    const PrintFn out = emit;

    if (opts.filePath)
    {
        std::string err;
        auto        games = load_games_from_file(*opts.filePath, err);
        if (!err.empty())
        {
            emit("gameanalysis error " + err);
            return err;
        }

        for (size_t i = 0; i < games.size(); ++i)
        {
            Options gopts = opts;
            gopts.fen       = games[i].fen;
            gopts.moves     = games[i].moves;
            gopts.filePath.reset();

            emit("gameanalysis game " + std::to_string(i + 1) + "/" + std::to_string(games.size())
                 + " moves " + std::to_string(games[i].moves.size()));

            if (auto e = run_single_game(engine, gopts, games[i], out))
            {
                emit("gameanalysis error " + *e);
                return e;
            }
        }
        return std::nullopt;
    }

    GameSpec game{opts.fen, opts.moves};
    if (auto e = run_single_game(engine, opts, game, out))
    {
        emit("gameanalysis error " + *e);
        return e;
    }
    return std::nullopt;
}

}  // namespace Stockfish::GameAnalysis
