# hydra-lsf-launcher

This is a simple launcher for launching Hydra jobs on LSF clusters. It is a simple wrapper around the `bsub` command that allows you to launch Hydra jobs with a single command.

**Run at your own risk, expect bugs. This is not an official Hydra project.**

Here is an example using hydra-zen to launch a job on an LSF cluster:

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

