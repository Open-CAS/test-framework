# Test framework for Open-CAS Linux
This framework consists of API and test suite for [Open-CAS Linux](https://github.com/Open-CAS/open-cas-linux).

## How to run tests?
Make sure you have a device with at least 2 disks (one for cache and one core). Be careful as these devices will be most likely overwritten
with random data during tests. Tests can be either executed locally or on a remote platform specified in the [dut_config](config/example_dut_config.py).
1. Edit [config/configuration.py](config/configuration.py) file in order to set [Open-CAS Linux](https://github.com/Open-CAS/open-cas-linux) repo path.
You can also set additional options in there.
2. As mentioned before tests can be either executed locally or on a remote platform specified in the [dut_config](config/example_dut_config.py).
    a) For local execution remove the line setting ip in the [dut_config](config/example_dut_config.py).  
    b) For remote execution set the ip value in the [dut_config](config/example_dut_config.py).
3. Set disks params in [dut_config](config/example_dut_config.py) (for remote execution also set user and password)
4. Run with ```pytest --dut-config=example_dut_config``` or any other created dut_config
