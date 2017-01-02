@set CONFIG=mini_meter
@cd /d %~dp0
python meter.py %CONFIG%.json > %CONFIG%.csv
python ..\..\vmdgadgets\spectrum.py --config %CONFIG%.json %1
timeout 10
