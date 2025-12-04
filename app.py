# app.py
from flask import Flask, render_template_string, request, jsonify
import numpy as np
import copy
import random

app = Flask(__name__)

# ----- ゲームロジック -----
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0), (1, 1)
]

def init_board():
    b = np.zeros((8,8), dtype=int)
    b[3,3] = 2; b[3,4] = 1; b[4,3] = 1; b[4,4] = 2
    return b

def board_to_list(board):
    return board.tolist()

def valid_moves(board, player):
    moves = []
    opponent = 2 if player == 1 else 1
    for r in range(8):
        for c in range(8):
            if board[r][c] != 0: continue
            legal = False
            for dr, dc in DIRECTIONS:
                rr, cc = r+dr, c+dc
                found_op = False
                while 0 <= rr < 8 and 0 <= cc < 8:
                    if board[rr][cc] == opponent:
                        found_op = True
                    elif board[rr][cc] == player and found_op:
                        legal = True; break
                    else:
                        break
                    rr += dr; cc += dc
                if legal:
                    moves.append((r,c)); break
    return moves

def apply_move(board, row, col, player):
    opponent = 2 if player == 1 else 1
    nb = copy.deepcopy(board)
    nb[row][col] = player
    for dr, dc in DIRECTIONS:
        r, c = row+dr, col+dc
        flip = []
        while 0 <= r < 8 and 0 <= c < 8 and nb[r][c] == opponent:
            flip.append((r,c))
            r += dr; c += dc
        if 0 <= r < 8 and 0 <= c < 8 and nb[r][c] == player:
            for rr, cc in flip:
                nb[rr][cc] = player
    return nb

def ai_move(board, player):
    moves = valid_moves(board, player)
    if not moves: return None
    best_moves=[]; best_gain=-10**9
    for (r,c) in moves:
        nb = apply_move(board, r, c, player)
        gain = int((nb == player).sum() - (board == player).sum())
        if gain > best_gain:
            best_gain = gain; best_moves=[(r,c)]
        elif gain == best_gain:
            best_moves.append((r,c))
    return random.choice(best_moves)

def game_over(board):
    return len(valid_moves(board,1))==0 and len(valid_moves(board,2))==0

def score(board):
    return int((board==1).sum()), int((board==2).sum())

# ----- ゲーム状態 -----
game_state = {
    "board": init_board(),
    "current": None  # None = 先攻後攻未選択
}

# ----- HTML -----
INDEX_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Othello (Human vs AI)</title>
<style>
  body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px;background:#fafafa}
  #board{display:grid;grid-template-columns:repeat(8,48px);gap:4px;margin-bottom:12px;}
  .cell{width:48px;height:48px;background:#2e7d32;border-radius:6px;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:rgba(0,0,0,0.2) 0 1px 3px}
  .cell.empty{background:#4caf50}
  .stone.x{width:36px;height:36px;border-radius:50%;background:#111;color:white;display:flex;align-items:center;justify-content:center}
  .stone.o{width:36px;height:36px;border-radius:50%;background:#fafafa;display:flex;align-items:center;justify-content:center}
  #info{margin-bottom:8px}
  button{padding:8px 12px;border-radius:6px;border:0;background:#0288d1;color:white;cursor:pointer;margin-right:6px}
  #moves{font-size:14px;color:#333}
</style>
</head>
<body>
  <h2>Othello — Human (X) vs AI (O)</h2>
  <div id="choice">
    <button onclick="startGame(1)">先攻で始める (You start)</button>
    <button onclick="startGame(2)">後攻で始める (AI starts)</button>
  </div>
  <div id="info" style="display:none;">
    <span id="status">Loading...</span>
    <button id="restart">Restart</button>
  </div>
  <div id="board" role="grid"></div>
  <div id="moves"></div>

<script>
let boardElem = document.getElementById('board');
let status = document.getElementById('status');
let movesDiv = document.getElementById('moves');
let choiceDiv = document.getElementById('choice');
let infoDiv = document.getElementById('info');

async function fetchState(){
  const res = await fetch('/state');
  return res.json();
}

function renderBoard(b){
  boardElem.innerHTML = '';
  for(let r=0;r<8;r++){
    for(let c=0;c<8;c++){
      const v = b[r][c];
      const cell = document.createElement('div');
      cell.className = 'cell ' + (v===0 ? 'empty' : '');
      cell.dataset.r = r; cell.dataset.c = c;
      if(v===1){
        const s = document.createElement('div'); s.className='stone x'; s.textContent='';
        cell.appendChild(s);
      } else if(v===2){
        const s = document.createElement('div'); s.className='stone o'; s.textContent='';
        cell.appendChild(s);
      }
      boardElem.appendChild(cell);
      cell.addEventListener('click', onClickCell);
    }
  }
}

function showMoves(list){
  movesDiv.textContent = 'Legal moves: ' + JSON.stringify(list);
}

async function onClickCell(e){
  const r = parseInt(this.dataset.r), c = parseInt(this.dataset.c);
  const res = await fetch('/move', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({r,c})
  });
  const js = await res.json();
  if(js.error){ alert(js.error); return; }
  renderBoard(js.board);
  status.textContent = js.msg;
  showMoves(js.legal);
  if(js.game_over){
    alert(js.msg + '\\nScore - X(black): '+js.score[0]+'  O(white): '+js.score[1]);
    choiceDiv.style.display = 'block';
    infoDiv.style.display = 'none';
  }
}

async function startGame(player){
  await fetch('/start', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({player})
  });
  choiceDiv.style.display = 'none';
  infoDiv.style.display = 'block';
  const s = await fetchState();
  renderBoard(s.board);
  status.textContent = s.msg;
  showMoves(s.legal);
}

document.getElementById('restart').addEventListener('click', async ()=>{
  choiceDiv.style.display = 'block';
  infoDiv.style.display = 'none';
  boardElem.innerHTML = '';
  movesDiv.textContent = '';
  await fetch('/restart', {method:'POST'});
});
</script>
</body>
</html>
"""

# ----- API: 現在の状態 -----
@app.route('/state')
def state():
    b = game_state['board']
    cur = game_state['current']
    legal = valid_moves(b, cur) if cur in [1,2] else []
    msg = ""
    if cur==1:
        msg = "Your turn (X)"
    elif cur==2:
        msg = "AI thinking..."
    else:
        msg = "Choose who starts"
    return jsonify(board=board_to_list(b), current=cur, legal=legal, msg=msg)

# ----- API: ゲーム開始（先攻後攻選択） -----
@app.route('/start', methods=['POST'])
def start():
    payload = request.get_json()
    player = int(payload.get("player", 1))
    game_state['board'] = init_board()
    game_state['current'] = player

    # AIが先攻なら1手打たせる
    if player == 2:
        mv = ai_move(game_state['board'], 2)
        if mv:
            game_state['board'] = apply_move(game_state['board'], mv[0], mv[1], 2)
        game_state['current'] = 1
    return jsonify(ok=True)

# ----- API: 人間の手 -----
@app.route('/move', methods=['POST'])
def move():
    payload = request.get_json()
    r = int(payload.get('r')); c = int(payload.get('c'))
    b = game_state['board']; cur = game_state['current']

    if cur != 1:
        return jsonify(error="It's not your turn.", board=board_to_list(b), legal=valid_moves(b,1)), 400

    legal = valid_moves(b,1)
    if (r,c) not in legal:
        return jsonify(error="Illegal move.", board=board_to_list(b), legal=legal), 400

    # apply human move
    b = apply_move(b, r, c, 1)
    game_state['board'] = b

    # AIターン
    if len(valid_moves(b,2))>0:
        mv = ai_move(b,2)
        if mv is not None:
            b = apply_move(b, mv[0], mv[1], 2)
            game_state['board'] = b

    # 次のターン決定
    if len(valid_moves(game_state['board'],1))>0:
        game_state['current'] = 1
    elif len(valid_moves(game_state['board'],2))>0:
        game_state['current'] = 2
    else:
        game_state['current'] = None

    sc = score(game_state['board'])
    msg = "Your turn (X)" if game_state['current']==1 else ("AI moved" if game_state['current']==2 else "Game over")
    return jsonify(board=board_to_list(game_state['board']), msg=msg, legal=valid_moves(game_state['board'],1), score=sc, game_over=(game_state['current'] is None))

# ----- Restart -----
@app.route('/restart', methods=['POST'])
def restart():
    game_state['board'] = init_board()
    game_state['current'] = None  # 選択画面に戻る
    return jsonify(ok=True)

# ----- index -----
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

if __name__ == '__main__':
    app.run(debug=True)
