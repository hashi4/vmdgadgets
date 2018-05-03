@rem 首・頭・目モーションを若干変更します
@rem 予め多段化したモデルのpmxファイル、モーション2種をsozaiディレクトリに用意
@rem workspaceディレクトリは中間生成物置き場

@set BASE1="sozai\JEWEL_多段ボーン.vmd"
@set BASE2="sozai\JEWEL_上半身2腕捩手捩足IK親.vmd"

@set WORKSPACE=workspace
@set VGPATH=..\..\..\vmdgadgets

if not exist %WORKSPACE% (
    mkdir %WORKSPACE%
)

@rem カメラ目線にしない部分を除外
python remove_frames.py jewel_camera.vmd %WORKSPACE%\cam_gaze.vmd

@rem 首以上は準標準ボーン版を利用、首より下は多段ボーン版を利用(衝突補正が楽なので)
python %VGPATH%\omit_motion.py -i -b 両目 -b 頭 -b 首 %BASE2%  %WORKSPACE%\head.vmd
@rem カメラのカットフレーム後の数フレームの頭モーション削除
python cut.py %WORKSPACE%\head.vmd %WORKSPACE%\cam_gaze.vmd %WORKSPACE%\head_cutted.vmd
python %VGPATH%\omit_motion.py -b 両目 -b 頭親1 -b 頭親2 -b 頭親3 -b 首 -b 両目 %BASE1%  %WORKSPACE%\body.vmd
@rem merge
python %VGPATH%\merge_vmd.py -i %WORKSPACE%\head_cutted.vmd %WORKSPACE%\body.vmd -o %WORKSPACE%\jewel.vmd

@rem 反転モーション作成と全ての親移動
python %VGPATH%\vmd_concat.py mirror.txt %WORKSPACE%\jewel_i.vmd
python %VGPATH%\move_root.py --pos -3.3 0 2 %WORKSPACE%\jewel_i.vmd %WORKSPACE%\jewel_i_moved.vmd
python %VGPATH%\move_root.py --pos 3.3 0 -2 %WORKSPACE%\jewel.vmd %WORKSPACE%\jewel_moved.vmd

@rem 首・頭・両目モーション調整(所要時間大) => left.vmd, right.vmd
call trace_camera.bat
