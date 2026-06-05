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

#ifndef GAME_ANALYSIS_H_INCLUDED
#define GAME_ANALYSIS_H_INCLUDED

#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace Stockfish {

class Engine;

namespace GameAnalysis {

constexpr int DefaultMaxPlies = 500;

struct GameSpec {
    std::string              fen;
    std::vector<std::string> moves;
};

struct Options {
    int  depth    = 0;
    int  multiPv  = 1;
    int  live     = 0;
    int  cold     = 0;
    int  resume   = 2;  // 0=full ID each ply 1=legacy 2=spine 3=same as 2 — cold 0 only
    int  resumeHorizon = 1;  // min ID plies to (re)run when resuming
    int  refine   = 1;  // end: cheap deepen where TT gained depth from later plies
    int  strict   = 0;  // 1 = full 1..D ID each ply (keep TT reuse); 0 = allow startDepth skip
    int  threads  = 0;  // 0 = use all logical CPUs
    int  maxPlies = DefaultMaxPlies;

    std::string fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    std::vector<std::string> moves;
    std::optional<std::string> filePath;
};

struct PvLine {
    int         multipv      = 0;
    int         depth        = 0;
    int         scoreCp      = 0;
    bool        isMate       = false;
    std::string scoreText;
    std::string pv;
    std::string pvFirstUci;
};

struct PlyResult {
    int                 gamePly = 0;
    std::string         fen;
    std::vector<PvLine> lines;
    int                 bestDepth = 0;
    uint64_t            nodes     = 0;
    uint64_t            timeMs    = 0;
    int                 hashfull  = 0;
};

struct Report {
    std::vector<PlyResult> plies;
    uint64_t               totalNodes  = 0;
    uint64_t               totalTimeMs = 0;
    int                    lastHashfull = 0;
};

using PrintFn = std::function<void(std::string_view)>;

std::optional<std::string> parse_options(std::istream& is, Options& opts);
std::vector<GameSpec>    load_games_from_file(const std::string& path, std::string& error);
std::optional<std::string> run(Engine& engine, const Options& opts, PrintFn print);

}  // namespace GameAnalysis
}  // namespace Stockfish

#endif  // #ifndef GAME_ANALYSIS_H_INCLUDED
