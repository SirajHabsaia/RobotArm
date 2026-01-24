from stockfish import Stockfish

stockfish = Stockfish(path=".stockfish/stockfish-windows-x86-64-avx2.exe")

stockfish.make_moves_from_start(["e2e4", "e7e6"])

best_move = stockfish.get_best_move()

print(f"The best move is: {best_move}")

print(stockfish.get_board_visual())