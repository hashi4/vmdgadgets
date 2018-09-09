@rem お借りしたものをsozaiディレクトリにコピーしておく

@rem 「すべての親」の位置・回転を変更
@rem ルカ: 位置(-14.5, 0, -0.5), 回転(0, 110, 0) => luka.vmd
@rem ミク: 位置(8.5, 0, 3.5), 回転(0, -70, 0) => miku.vmd

@rem しゃがむ所は要調整
@set MIKU="sozai\magミク別バージョン.vmd"
@set LUKA="sozai\magルカ別バージョン.vmd"

@set VGPATH=..\..\..\vmdgadgets
python %VGPATH%\move_root.py %MIKU% miku.vmd --pos -14.5 0 -0.5 --angle 0 110 0
python %VGPATH%\move_root.py %LUKA% luka.vmd --pos 8.5 0 3.5 --angle 0 -70 0

