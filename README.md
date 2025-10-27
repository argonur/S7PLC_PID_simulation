# S7PLC_PID_simulation

Learning and experimentation repository for PID control in Siemens PLCs using PLCSIM Advanced and OPC UA.

## Repository Structure

<!-- to do -->

## Python Virtual Environment

A virtual environment is required to install Python packages. The following commands create and activate a virtual environment, in addition to installing the necessary packages to run the software in this repository:

    ```sh
    python3 -m venv myVirtualEnv
    source myVirtualEnv/bin/activate
    pip install -r requirements.txt
    ```

However, after cleaning the workspace with `git clean -fdx`, the environment will disappear. The *setupVirtualEnv.sh* script can be used to recreate the virtual environment. The *requirements.txt* file is used by that script to install the necessary packages. **Run the script as follows to ensure the activation persists:**

    ```sh
    . setupVirtualEnv.sh
    ```

The *requirements.txt* file should be updated with `pip freeze > requirements.txt` if additional Python packages are installed.

If for any reason you need to deactivate the environment, you can do so with the `deactivate` command.
