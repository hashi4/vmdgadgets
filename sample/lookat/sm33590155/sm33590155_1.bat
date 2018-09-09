@rem sozaiディレクトリにお借りしたものをコピーしておく

@rem [右]: モーション反転, 全ての親を(4,5, 0, -2), センターと足IKの高さを0.85倍
@rem [左]: 全ての親を(-4,5, 0, 2), センターと足IKの高さを0.95倍

@set BASE="sozai\[A]ddiction_Tda式.vmd"
@set VGPATH=..\..\..\vmdgadgets
%VGPATH%\vmd_concat.py mirror.txt|python %VGPATH%\move_root.py --pos 4.5 0 -2 --angles 0 -3 0|%VGPATH%\scale_motion.py -s 1 0.85 1 > right_base.vmd
%VGPATH%\move_root.py %BASE% --pos -4.5 0 2 --angles 0 3 0|%VGPATH%\scale_motion.py -s 1 0.95 1 > left_base.vmd
