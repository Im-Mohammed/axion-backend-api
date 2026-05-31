@echo off

echo Staging changes...
git add .

set /p commit_message="Enter commit message: "

echo Committing...
git commit -m "%commit_message%"

echo Pushing to GitHub...
git push

echo Building Docker image...
docker build --no-cache -t mohammedkarab/moportfolio-backend:latest .

echo Pushing to Docker Hub...
docker push mohammedkarab/moportfolio-backend:latest

echo.
echo Done! Go to Render and click Manual Deploy.
pause