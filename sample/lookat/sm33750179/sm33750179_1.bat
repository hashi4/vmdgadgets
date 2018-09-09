@rem 事前にお借りしたものをsozaiディレクトリへコピーしておく

@set ORIG_MOTION="sozai\さとく式鶯丸(リップ表情付き).vmd"

@set VGPATH=..\..\..\vmdgadgets

@rem センター、足IKの移動を0.87倍
python %VGPATH%\scale_motion.py %ORIG_MOTION% plus_0.vmd -s 0.87

@rem グルーブや左足IK、表情破綻を適宜変更

@rem 5フレームづつずらす(つなぎ目は手作業で補正)
python shift.py plus_0.vmd

@rem 「すべての親」位置を変更
python %VGPATH%\move_root.py plus_0.vmd 1.vmd --pos -9 0 -9
python %VGPATH%\move_root.py plus_5.vmd 2.vmd --pos -3 0 -3
python %VGPATH%\move_root.py plus_10.vmd 3.vmd --pos 3 0 3
python %VGPATH%\move_root.py plus_15.vmd 4.vmd --pos 9 0 9
