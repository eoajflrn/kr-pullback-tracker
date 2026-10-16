"""Install code updates without replacing the user's cumulative data."""
from pathlib import Path
import shutil,datetime,sqlite3,sys

def install(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if source==target:raise ValueError('새 버전 폴더가 아니라 기존 사용 폴더를 선택하세요.')
    if not (target/'run.py').exists()or not (target/'data/tracker.db').exists():raise ValueError('기존 PREVIEW.cmd와 data 폴더가 있는 프로그램 폴더를 선택하세요.')
    backup=target/'backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True,exist_ok=False)
    old=sqlite3.connect(target/'data/tracker.db');saved=sqlite3.connect(backup/'tracker.db');old.backup(saved);saved.close();old.close()
    selected=[]
    for p in source.rglob('*'):
        rel=p.relative_to(source)
        if not p.is_file()or '__pycache__'in rel.parts:continue
        if rel.parts[0]in ('scanner','tests','.github')or rel.parts[0]=='web'and len(rel.parts)==2 or len(rel.parts)==1 and p.suffix in ('.py','.cmd','.md','.txt'):
            selected.append((p,rel))
    for p,rel in selected:
        dest=target/rel
        if dest.exists():
            b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,b)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    return backup
if __name__=='__main__':
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw()
    messagebox.showinfo('기존 기록 보존 업데이트','기존 서버 실행 창을 먼저 종료해 주세요. 기존 사용 폴더를 선택하면 코드만 교체하고 누적 DB와 가격 파일은 보존합니다.')
    folder=filedialog.askdirectory(title='기존 PREVIEW.cmd가 있는 폴더 선택')
    if folder:
        try:
            backup=install(Path(__file__).parent,folder);messagebox.showinfo('완료',f'업데이트 완료. 기존 폴더의 PREVIEW.cmd를 실행하세요.\n백업: {backup}')
        except Exception as e:messagebox.showerror('업데이트 실패',str(e));sys.exit(1)
