class Solution:
    def tictactoe(self, moves: List[List[int]]) -> str:
        row_a = [0] * 3
        col_a = [0] * 3
        row_b = [0] * 3
        col_b = [0] * 3
        for i, grid in moves:
            if i%2 == 0:
                for place in grid:
                    row_a[place] += 1
                    col_a[place] += 1
                    if '3' in row or '3' in col:
                        return "A"
            else:
                for place in grid:
                    row_b[place] += 1
                    col_b[place] += 1
                    if '3' in row or '3' in col:
                        return "B"
        return "Draw"

# 注意正负对角线问题
class Solution:
    def tictactoe(self, moves: List[List[int]]) -> str:
        
        row_a = [0] * 3
        col_a = [0] * 3
        row_b = [0] * 3
        col_b = [0] * 3
        diag_a = 0
        diag_b = 0
        re_diag_a = 0
        re_diag_b = 0
        for i, (r, c) in enumerate(moves):
            if i%2 == 0:
                row_a[r] += 1
                col_a[c] += 1
                if r==c:
                    diag_a += 1
                if r+c==2:
                    re_diag_a+=1
                if 3 in row_a or 3 in col_a or diag_a==3 or re_diag_a==3:
                    return "A"
            else:
                row_b[r] += 1
                col_b[c] += 1
                if r==c:
                    diag_b += 1
                if r+c==2:
                    re_diag_b+=1
                if 3 in row_b or 3 in col_b or diag_b==3 or re_diag_b==3:
                    return "B"
        if len(moves)==9:
            return "Draw"
        else:
            return "Pending"