"# LCB1-RTG" 
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ssh_rtg
lcb1rtg
git pull origin main