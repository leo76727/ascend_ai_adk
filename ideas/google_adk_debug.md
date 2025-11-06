{
            "name": "adk web",
            "type": "debugpy",
            "request": "launch",
            "module": "google.adk.cli",
            "cwd": "${workspaceFolder}/",
            "envFile": "${workspaceFolder}/.env",
            "justMyCode": false,
            "args": [
                "web",
                "--no-reload",
                "--log_level",
                "debug",
            ]
        }
Thanks!

I instead run the "adk run" command with the current folder as input. This way I can quickly test in the terminal if subagents work correctly. Here is my config:

        {
            "name": "adk run",
            "type": "debugpy",
            "request": "launch",
            "module": "google.adk.cli",
            "cwd": "${workspaceFolder}/",
            "envFile": "${workspaceFolder}/code/.env",
            "justMyCode": false,
            "args": [
                "run",
                "${fileDirname}"
            ]
        },


# fast api server for adk
https://gist.github.com/Alphanimble/3d51057bc6fe2e154d2a5a17164e9a9e


#override adk web
https://github.com/google/adk-python/pull/2967/files#diff-b4bcf965324bcbc35ec1562cde8413c441bd841a99f5ec958dcc65c7155922e8