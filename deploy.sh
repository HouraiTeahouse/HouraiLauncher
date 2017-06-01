#!/bin/bash
ls -lah dist/*
for file in $(ls dist/*)
do
curl -i -X POST $DEPLOY_UPLOAD_URL/$TRAVIS_BRANCH/$TRAVIS_OS_NAME?token=$TOKEN \
        -T $file
done
