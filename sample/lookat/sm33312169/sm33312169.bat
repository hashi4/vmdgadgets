@rem お借りしたものをsozaiディレクトリへコピーして、本ファイル実行
@rem motion1.vmd, motion2.vmd, motion3.vmd が出来上がるので
@rem MMD上でをそれぞれ中央、右、左モデルへ適用

@rem model
@set MODEL1="sozai\秦始皇.pmx"
@set MODEL2="sozai\朱棣.pmx"
@SET MODEL3="sozai\康熙 Kawaii Strike.pmx"

@rem motion
@set MOTION1="sozai\tda_center.vmd"
@set MOTION2="sozai\tda_right.vmd"
@set MOTION3="sozai\tda_left.vmd"

@rem camera
@set CAMERA="sozai\桃源恋歌３人女子用.vmd"

@set EYES_CONST=--constraint 両目 9 12 0 0.15 0.15 0
@set HEAD_CONST=--constraint 頭 60 60 60 0.4 0.35 0
@set NECK_CONST=--constraint 首 60 60 60 0.1 0.1 0
@set IGNORE=--ignore 80
@set FRAME_RANGES=--frame_range 946 2325 --frame_range 2769 4131 --frame_range 5005 6600

@set VGPATH=..\..\..\vmdgadgets

python %VGPATH%\trace_camera.py %MODEL1% %MOTION1% %CAMERA% head1.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION1%|python %VGPATH%\merge_vmd.py -i - head1.vmd -o motion1.vmd

python %VGPATH%\trace_camera.py %MODEL2% %MOTION2% %CAMERA% head2.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION2%|python %VGPATH%\merge_vmd.py -i - head2.vmd -o motion2.vmd

python %VGPATH%\trace_camera.py %MODEL3% %MOTION3% %CAMERA% head3.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION3%|python %VGPATH%\merge_vmd.py -i - head3.vmd -o motion3.vmd
