@rem 首・頭・両目モーションを微調整します
@rem モデル、モーション、カメラの各ファイルを予めsozaiディレクトリに用意
@rem 実行後、312フレーム目他、気になる所を手で調整(60FPS時)

@set MODEL="sozai\MiraiAkari_v1.0.pmx"
@set MOTION="sozai\Masked bitcH.vmd"
@set CAMERA="sozai\低身長用カメラモーションver1.01.vmd"

@rem tekitou
@set EYES_CONST=--constraint 両目 10 15 0 .15 .15 0
@set HEAD_CONST=--constraint 頭 40 40 40 .1 .1 0
@set NECK_CONST=--constraint 首 60 60 60 .3 .3 0
@set IGNORE=--ignore 90

@set VGPATH=..\..\vmdgadgets
@rem 頭・首・両目モーション調整 => head.vmd
python %VGPATH%\trace_camera.py %MODEL% %MOTION% %CAMERA% head.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %IGNORE% --frame_range 275 9999
@rem その他モーションと合成 => merged.vmd
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION%|python %VGPATH%\merge_vmd.py -i - head.vmd -o merged.vmd
