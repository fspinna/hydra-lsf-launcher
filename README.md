# hydra-lsf-launcher
This is a simple launcher for launching Hydra jobs on LSF clusters. It is a simple wrapper around the `bsub` command that allows you to launch Hydra jobs with a single command.

### **WARNING: expect bugs and run at your own risk. This is not an official Hydra project.**

## Installation
Install the package with pip:
```bash
pip install hydra-lsf-launcher
```

## Usage

Here is an example using `hydra-zen` to launch a job on an LSF cluster:

```python
from hydra_zen import store, zen
import time


def main_func(sentence):
    time.sleep(120)
    print(sentence)


store(
    main_func,
    hydra_defaults=[
            "_self_",
    ]
)


if __name__ == "__main__":
    store.add_to_hydra_store()
    zen(main_func).hydra_main(
        config_name="main_func", version_base="1.1", config_path=None
    )
```

Then you can run it with:

```bash
python myscript.py hydra/launcher=lsf sentence="Hello World!" -m 
```

## Job groups

To limit the number of concurrent jobs, as for now job arrays are not supported, the user can set job groups:

```bash
bgadd /myJobGroup
bgmod -L 32 /myJobGroup  # limit to 32 concurrent jobs
```



Then you can run it with:

```bash
python myscript.py hydra/launcher=lsf hydra.launcher.bsub_args="-g /myJobGroup" sentence="Hello World!" -m 
```

Some useful commands.
To change the limit of a job group:
```bash
bgmod -L <new_limit> /myJobGroup
```

To delete a job group:
```bash
bgdel /myJobGroup
```

