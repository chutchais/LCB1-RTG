"# LCB1-RTG" 
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ssh_rtg
lcb1rtg
git pull origin main
docker-compose up -d --build


#Create Volumn RTG
1)Create volumes named "rtg"

>docker volume create --name rtg \
--opt type=none --opt device=/opt/rtg \
--opt o=bind

2)Check volume is exist
>docker volume ls

**must see volume name "rtg"