echo "Branch: %APPVEYOR_REPO_BRANCH%"
echo "Pull Request: %APPVEYOR_PULL_REQUEST_NUMBER%"
if "%APPVEYOR_REPO_BRANCH%" == "master" (
        echo "Starting Deployment..."
        for /r %%i in (dist/*) do echo %%i

        for %%f in (dist/*) do (
        echo "Deploying %%f"
        curl.exe -i -X POST "%DEPLOY_UPLOAD_URL%/%APPVEYOR_REPO_BRANCH%/Windows?token=%TOKEN%" ^
                -F "file=@dist/%%f" ^
                --keepalive-time 2
        )
        echo "Finished deployment..."
)
