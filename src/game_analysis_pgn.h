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

#ifndef GAME_ANALYSIS_PGN_H_INCLUDED
#define GAME_ANALYSIS_PGN_H_INCLUDED

#include <string>
#include <vector>

#include "game_analysis.h"

namespace Stockfish::GameAnalysis {

bool is_pgn_path(const std::string& path);

// Parse one or more games from a PGN file into GameSpec (FEN + UCI moves).
std::vector<GameSpec> load_games_from_pgn(const std::string& path, std::string& error);

// Convert SAN movetext to UCI using a temporary Position (for tests / validation).
std::optional<std::string> san_movetext_to_uci(const std::string& fen, bool chess960,
                                               const std::vector<std::string>& sans,
                                               std::vector<std::string>& uciOut);

}  // namespace Stockfish::GameAnalysis

#endif  // #ifndef GAME_ANALYSIS_PGN_H_INCLUDED
