run_serv:
	poetry run python3 rc_tp01/server.py $(arg1) $(arg2) $(arg3)

run_cli:
	poetry run python3 rc_tp01/client.py $(arg1) $(arg2)

demo:
	$(MAKE) run_serv arg1=5555 arg2=1234 arg3=6 &
	sleep 2
	$(MAKE) run_cli arg1=localhost arg2=5555