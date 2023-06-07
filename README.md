# Sentiment Classifier DApp

This example shows how to build a Python-based DApp that uses a regular scikit-learn model to perform sentiment classification on an input sentence. The DApp accepts sentences as input and will generate a notice containing one of the three classes: positive, neutral or negative. The supplied model is a Multinomial Naïve Bayes trained externally on the [Twitter US Airline Sentiment](https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment) dataset.

The goal of the example is to demonstrate the installation and use of python packages that have parts written in other languages and might have to be compiled for RISC-V architecture.

## Building the DApp

The `requirements.txt` file has all python dependencies with version pinned, and was generated from `requirements.in` file by [pip-tools](https://pip-tools.readthedocs.io/en/latest/). This is done in order to ensure the inference code will use the same versions used during training, improving reproducibility. However, as of writing of this code, there is no pre-built wheels for RISC-V published in PyPI. We therefore have to either compile them during the build process or build the wheels externally.

The steps below show how to build the wheels externally, in a emulated Docker container, and later how to take
advantage of the precompiled wheels to build the final application.

### Building dependencies

To compile the external dependencies, a separate image can be built with the `Dockerfile.builder` file. This image includes dependencies that are required for the build process but are not needed for the final application. Build this image with the following command:

```console
docker build -f Dockerfile.builder . -t cartesi-python-builder:latest
```

Once we have the image, we can start building the wheels, which will be stored in the `wheels` directory. Warning: this process can take several hours to complete.

```console
docker run --rm -it \
    -v $PWD:/opt/cartesi/dapp \
    -u $EUID:${GROUPS[0]} \
    --platform=linux/riscv64 cartesi-python-builder:latest \
    pip wheel -r requirements.txt -w wheels
```

### Creating the alternative package index

The `wheels` directory created in the last step should now contain all the generated wheel files. In order to have a [PEP 503](https://peps.python.org/pep-0503/) compliant package index structure we have to move the resulting files so
that each one resides in a subdirectory named after its package. This can be accomplished by running the following bash oneliner inside the wheels directory:

```console
for filename in *.whl; do package=$(echo $filename | cut -d- -f 1 | sed -e 's/_/-/g'); mkdir -p $package; mv $filename $package; done
```

The resulting directory structure should be as follows:

```console
$ tree
.
├── certifi
│   └── certifi-2022.12.7-py3-none-any.whl
├── charset_normalizer
│   └── charset_normalizer-3.1.0-py3-none-any.whl
├── idna
│   └── idna-3.4-py3-none-any.whl
├── joblib
│   └── joblib-1.2.0-py3-none-any.whl
├── numpy
│   └── numpy-1.24.2-cp310-cp310-linux_riscv64.whl
├── requests
│   └── requests-2.28.2-py3-none-any.whl
├── scikit_learn
│   └── scikit_learn-1.2.2-cp310-cp310-linux_riscv64.whl
├── scipy
│   └── scipy-1.10.1-cp310-cp310-linux_riscv64.whl
├── threadpoolctl
│   └── threadpoolctl-3.1.0-py3-none-any.whl
└── urllib3
    └── urllib3-1.26.15-py2.py3-none-any.whl
```

A simple way to serve the contents of this directory via HTTP is to run the simple HTTP server built into Python, with the following command:

```console
python -m http.server
```

Please note that since we don't want this wheel directory in the final image, it would be best to move it to somewhere outside the current repository.

### Building the final image

Once we have the wheel files generated, organized in the Package Index structure and being served via HTTP, we can now proceed with the ordinary docker-riscv build flow, but adding the necessary build arguments that will instruct pip to use our newly created alternate package index. This can be done as below, changing `[hostname]` for the hostname of the computer running the command from the last step:

```console
docker buildx bake --load \
    --set dapp.args.PIP_EXTRA_INDEX_URL=http://[hostname]:8000/ \
    --set dapp.args.PIP_TRUSTED_HOST=[hostname] \
    --set dapp.args.PIP_ONLY_BINARY=:all:
```

The last parameter will also instruct pip to never try building something from source. This way, if the requirements change and a new package that needs compiling is added, the build will fail and let you know you have to perform the necessary steps for building it.

## Running unit tests inside the Cartesi VM

In the local development environment, running test is as simple as calling `python -m unittest`. However, to run them in its production environment inside the Cartesi VM, you can spawn a console session perform the same command:

```console
$ docker run --rm -it cartesi/dapp:sentiment-devel-console
Running in interactive mode!
         .
        / \
      /    \
\---/---\  /----\
 \       X       \
  \----/  \---/---\
       \    / CARTESI
        \ /   MACHINE
         '
$ cd /opt/cartesi/dapp
$ python -m unittest
..
----------------------------------------------------------------------
Ran 2 tests in 5.669s

OK
```

This can also be done in a single command:

```console
docker run -it --name=sentiment-benchmark \
    cartesi/dapp:sentiment-devel-console \
        cartesi-machine --ram-length=128Mi \
                        --rollup \
                        --flash-drive=label:root,filename:dapp.ext2 \
                        --ram-image=linux.bin \
                        --rom-image=rom.bin -i \
                        -- "cd /opt/cartesi/dapp; python -m unittest"
```

## Interacting with the application

We can use the [frontend-console](../frontend-console) application to interact with the DApp.
Ensure that the [application has already been built](../frontend-console/README.md#building) before using it.

First, go to a separate terminal window and switch to the `frontend-console` directory:

```shell
cd frontend-console
```

Then, send an input sentence as follows:

```shell
yarn start input send --payload "This is a great example"
```

The results for the inference will be sent as a notice. The notices can be viewed with the command:

```shell
yarn start notice list
```

## Running the environment in host mode

When developing an application, it is often important to easily test and debug it. For that matter, it is possible to run the Cartesi Rollups environment in [host mode](../README.md#host-mode), so that the DApp's back-end can be executed directly on the host machine, allowing it to be debugged using regular development tools such as an IDE.

This DApp's back-end is written in Python, so to run it in your machine you need to have `python3` installed.

In order to start the back-end, run the following commands in a dedicated terminal:

```shell
cd sentiment/
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 sentiment.py
```

The final command will effectively run the back-end and send corresponding outputs to port `5004`.
It can optionally be configured in an IDE to allow interactive debugging using features like breakpoints.

You can also use a tool like [entr](https://eradman.com/entrproject/) to restart the back-end automatically when the code changes. For example:

```shell
ls *.py | ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" entr -r python3 sentiment.py
```

After the back-end successfully starts, it should print an output like the following:

```log
INFO:__main__:HTTP rollup_server url is http://127.0.0.1:5004
INFO:__main__:Sending finish
```

After that, you can interact with the application normally [as explained above](#interacting-with-the-application).
