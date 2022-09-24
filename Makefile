.PHONY: deploy
deploy:
	rsync -avzr --progress ./bot.py   root@hdl-bot.lan:/opt/hdlbot/bot.py; \
	rsync -avzr --progress ./admin_bot.py   root@hdl-bot.lan:/opt/hdlbot/admin_bot.py; \
	rsync -avzr --progress ./models.py   root@hdl-bot.lan:/opt/hdlbot/models.py; \
	rsync -avzr --progress ./schemas.py   root@hdl-bot.lan:/opt/hdlbot/schemas.py; \
	rsync -avzr --progress ./crud.py   root@hdl-bot.lan:/opt/hdlbot/crud.py;
