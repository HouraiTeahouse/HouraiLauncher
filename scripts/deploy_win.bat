if %APPVEYOR_REPO_BRANCH% == "master" (
        for /r %%i in (dist/*) do echo %%i

        for %%f in (dist/*) do (
        curl.exe -i -X POST "%DEPLOY_UPLOAD_URL%/%APPVEYOR_REPO_BRANCH%/Windows?token=%TOKEN%" ^
                -F "file=@dist/%%f" ^
                --keepalive-time 2
        )
)
