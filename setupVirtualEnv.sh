#!/bin/bash

echo "Creating Virtual Environment"
python3 -m venv myVirtualEnv
echo "Activating Virtual Environment"
source myVirtualEnv/bin/activate
echo "Install needed packages"
pip install -r requirements.txt

pip install -e .