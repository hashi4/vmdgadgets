cd /d %~dp0

@if "%CAMERA%"==""  (
    set CAMERA=edit\camera.vmd
)
@if "%MOTION%"=="" (
    set MOTION=left_base.vmd
)
@if "%HEAD_MOTION%"=="" (
    set HEAD_MOTION=left_head.vmd
)
@if "%EXT_MOTION%"=="" (
    set EXT_MOTION=stage.vmd
)
@if "%HEAD_MOTION%"=="left_head.vmd" (
    set MODEL=sozai\óÈíJâ¸ìÒ.pmx
    set FRAME_RANGE=--frame_range 240 9999
) else (
    set MODEL=sozai\åFñÏâ¸ìÒ.pmx
)

@set NECK_CONST=--constraint éÒ 10 10 25 .2 0.2 0
@set HEAD_CONST=--constraint ì™ 60 60 25 .5 0.4 0
@set EYES_CONST=--constraint óºñ⁄ 10 20 0 0.55 0.4 0
@set HEAD_BLEND=--vmd_blend ì™ 0.1 0.1 0
@set ADD_FRAMES=--add_frames 95 152

@set EXT_LINK=--extlink1 ÉZÉìÉ^Å[ "edit\plane.pmx" %EXT_MOTION%

python ..\..\..\vmdgadgets\trace_camera.py %MODEL% %MOTION% %CAMERA% %HEAD_MOTION% %NECK_CONST% %HEAD_CONST% %EYES_CONST% %NECK_BLEND% %HEAD_BLEND% %FRAME_RANGE% %ADD_FRAMES% --near --vmd_lerp %FRAME_RANGE% %EXT_LINK%
