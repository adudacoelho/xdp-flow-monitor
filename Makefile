# Demonstração: execute na raiz do projeto, no servidor.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
LAB_DIR := $(PROJECT_ROOT)/testes/testes-chen
RUN ?= demo-r1
DURATION ?= 180
PPS ?= 600
export RUN DURATION PPS
CSV ?= $(PROJECT_ROOT)/xdp-flow-monitor-main/dataset/synthetic_ddos.csv
MODEL ?= $(PROJECT_ROOT)/xdp-flow-monitor-main/ddos_model.ubj
SAMPLES ?= 10
CSV_PYTHON ?= $(if $(wildcard $(PROJECT_ROOT)/.venv/bin/python),$(PROJECT_ROOT)/.venv/bin/python,python3)
export CSV MODEL SAMPLES CSV_PYTHON

.PHONY: help demo-check demo-ping demo-server demo-monitor demo-traffic demo-log
help:
	@echo 'demo-csv-check — conferir CSV e modelo offline'
	echo 'demo-csv       — apresentar uma amostra por Enter (um terminal)'
	echo 'demo-csv-docker — mesma demo usando a imagem chen-lab:local'
	@echo 'demo-check   — conferir laboratório e compilar'
	echo 'demo-detector — iniciar monitor + XGBoost (180 s)'
	echo 'demo-screen   — painel para o projetor'
	echo 'demo-normal   — TCP limitado a 1 Mbit/s (60 s)'
	echo 'demo-attack   — carga SYN simulada (20 s, 600 pps solicitados)'
	echo 'demo-ping    — mostrar conexão generator → target'
	echo 'demo-server  — iniciar iperf no target (600 s)'
	echo 'demo-monitor — coletar com XDP/eBPF (70 s)'
	echo 'demo-traffic — gerar tráfego TCP (50 s)'
	echo 'demo-log     — acompanhar métricas ao vivo'
	echo 'Use RUN=demo-r2 para repetir monitor, traffic e log.'

demo-check:
	$(MAKE) -C "$(LAB_DIR)" clab-status
	$(MAKE) -C "$(LAB_DIR)" clab-check
	$(MAKE) -C "$(LAB_DIR)" clab-build

demo-ping:
	sudo docker exec clab-chen-generator ping -c 4 192.168.157.20

demo-server:
	sudo docker exec -it clab-chen-target make -C /workspace/testes/testes-chen/containers serve SERVICE=iperf DURATION=600 RUN=demo-server

demo-monitor:
	[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]]
	sudo docker exec -it clab-chen-target make -C /workspace/testes/testes-chen/containers observe MODE=collection-current DURATION=70 RUN="$$RUN"

demo-traffic:
	[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]]
	sudo docker exec -it clab-chen-generator make -C /workspace/testes/testes-chen/containers traffic KIND=tcp DURATION=50 RUN="$$RUN"

demo-log:
	@[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]] || { echo 'RUN inválido.' >&2; exit 1; }
	shopt -s nullglob
	logs=("$(LAB_DIR)"/results-servidor/target/*-observe-"$$RUN"/monitor.log)
	if (( $${#logs[@]} == 0 )); then echo 'Inicie a observação e espere PRONTO antes de abrir o log.' >&2; exit 1; fi
	sudo tail -n 30 -f "$${logs[-1]}"

.PHONY: demo-detector demo-screen demo-normal demo-attack
demo-detector:
	@[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]]
	sudo docker exec -it clab-chen-target make -C /workspace/testes/testes-chen/containers observe MODE=detector-current DURATION="$$DURATION" RUN="$$RUN"

demo-screen:
	@sudo python3 "$(PROJECT_ROOT)/scripts/demo_screen.py" --results "$(LAB_DIR)/results-servidor/target" --run "$$RUN"

demo-normal:
	@echo 'TRAFEGO TCP DE REFERENCIA — 1 Mbit/s por 60 segundos'
	echo 'A classificacao sera a resposta real do modelo, inclusive se houver falso positivo.'
	sudo docker exec -it clab-chen-generator timeout --signal=TERM --kill-after=5 75 iperf3 -c 192.168.157.20 -B 192.168.157.10 -p 80 -b 1M -t 60 -i 1

demo-attack:
	@[[ "$$RUN" =~ ^[a-zA-Z0-9_-]+$$ ]]
	echo 'CARGA SIMULADA NO LABORATORIO — origens .101 a .106'
	sudo docker exec -it clab-chen-generator make -C /workspace/testes/testes-chen/containers traffic KIND=syn DURATION=20 PPS="$$PPS" RUN="$$RUN"

.PHONY: demo-csv demo-csv-check demo-csv-docker
demo-csv-check:
	@"$$CSV_PYTHON" "$(PROJECT_ROOT)/scripts/demo_csv.py" --csv "$$CSV" --model "$$MODEL" --samples "$$SAMPLES" --check

demo-csv:
	@"$$CSV_PYTHON" "$(PROJECT_ROOT)/scripts/demo_csv.py" --csv "$$CSV" --model "$$MODEL" --samples "$$SAMPLES"

demo-csv-docker:
	@sudo docker run --rm -it --network none --read-only --cap-drop ALL --security-opt no-new-privileges -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -v "$(PROJECT_ROOT):/demo:ro" -w /demo chen-lab:local /workspace/.venv/bin/python /demo/scripts/demo_csv.py --csv /demo/xdp-flow-monitor-main/dataset/synthetic_ddos.csv --model /demo/xdp-flow-monitor-main/ddos_model.ubj --samples "$$SAMPLES"
