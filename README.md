# OpenBehavior: A Behavior-Centric Scenario Description Language for Autonomous Driving Testing

<!-- PROJECT LOGO -->

## [Project Page](http://www.katrinrenz.de/plant) | [Paper](https://arxiv.org/abs/2210.14222) | [Supplementary](https://www.katrinrenz.de/plant/resources/PlanT_supp.pdf) 

<p align="center">
  <img src="images/Roadmap.pdf" width="85%">
</p>

## Examples Video

### S1 T Junction

<details>
<summary><strong>R1-T</strong></summary>

<table>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-T1/out.gif" width="240"><br>
      <b>R1-T1</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-T2/out.gif" width="240"><br>
      <b>R1-T2</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-T3/out.gif" width="240"><br>
      <b>R1-T3</b>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-T4/out.gif" width="240"><br>
      <b>R1-T4</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-T5/out.gif" width="240"><br>
      <b>R1-T5</b>
    </td>
  </tr>
</table>
</details>

### S2 X Junction

<details>
<summary><strong>R1-X</strong></summary>

<table>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-X1/out.gif" width="240"><br>
      <b>R1-X1</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-X2/out.gif" width="240"><br>
      <b>R1-X2</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-X3/out.gif" width="240"><br>
      <b>R1-X3</b>
    </td>
  </tr>
</table>
</details>

### S3 Highway

<details>
<summary><strong>R1-L</strong></summary>

<table>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-L1/out.gif" width="240"><br>
      <b>R1-L1</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L2/out.gif" width="240"><br>
      <b>R1-L2</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L3/out.gif" width="240"><br>
      <b>R1-L3</b>
    </td>
  </tr>
   <tr>
    <td align="center">
      <img src="traffic_video/R1-L4/out.gif" width="240"><br>
      <b>R1-L4</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L5/out.gif" width="240"><br>
      <b>R1-L5</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L6/out.gif" width="240"><br>
      <b>R1-L6</b>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-L7/out.gif" width="240"><br>
      <b>R1-L7</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L8/out.gif" width="240"><br>
      <b>R1-L8</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L9/out.gif" width="240"><br>
      <b>R1-L9</b>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-L10/out.gif" width="240"><br>
      <b>R1-L10</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L11/out.gif" width="240"><br>
      <b>R1-L11</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L12/out.gif" width="240"><br>
      <b>R1-L12</b>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="traffic_video/R1-L13/out.gif" width="240"><br>
      <b>R1-L13</b>
    </td>
    <td align="center">
      <img src="traffic_video/R1-L14/out.gif" width="240"><br>
      <b>R1-L14</b>
    </td>
  </tr>
</table>

</details>

### R2 Unable to reach the destination

<details>
<summary><strong>R2</strong></summary>

<table>
  <tr>
    <td align="center">
      <img src="traffic_video/R2-1/out.gif" width="240"><br>
      <b>R2-1</b>
    </td>
    <td align="center">
      <img src="traffic_video/R2-2/out.gif" width="240"><br>
      <b>R2-2</b>
    </td>
    <td align="center">
      <img src="traffic_video/R2-3/out.gif" width="240"><br>
      <b>R2-3</b>
    </td>
  </tr>
</table>
</details>

<div align="center">
<p align="center">
    <br />
    <a href="xxx">View Details Demo</a>
  </p>

</div>

<!-- ABOUT THE PROJECT -->

## About The Project

This page presents multiple categories of bugs discovered in the Apollo autonomous driving system.

<!-- GETTING STARTED -->

## Getting Started

### Prerequisites

1. Install Carla(0.9.13)

   - Download from https://github.com/carla-simulator/carla/releases.

   - Extract the carla installation package to a directory.

     On Ubuntu systems, the Carla environment variable is configured as follows:

     ```
     export CARLA_ROOT=/home/xxx/CARLA_0.9.13
     export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg:${CARLA_ROOT}/PythonAPI/carla/agents:${CARLA_ROOT}/PythonAPI/carla/agents/navigation:${CARLA_ROOT}/PythonAPI/carla:${CARLA_ROOT}/PythonAPI/examples:${CARLA_ROOT}/PythonAPI
     ```

     

2. Setup Apollo8.0

   - Get apollo8.0

     ```
     git clone -b v8.0.0 https://github.com/ApolloAuto/apollo.git
     ```

   - Follow the official manunal to install

3. Setup Carla_apollo_bridge

   - Get the carla_apollo_bridge fromhttps://github.com/MaisJamal/carla_apollo_bridge
   - Follow the readme to install

4. Make Env

   1. Prepare for srunner

      - Install JDK

        ```
        sudo apt install openjdk-17-jdk
        ```

      - Install Antlr 4.10.1

        ```
        sudo apt install curl
        curl -O https://www.antlr.org/download/antlr-4.10.1-complete.jar
        sudo cp antlr-4.10.1-complete.jar /usr/local/lib/
        
        sudo gedit ~/.bashrc
        # add 
        export CLASSPATH=".:/usr/local/lib/antlr-4.10.1-complete.jar:$CLASSPATH"
        alias antlr4='java -jar /usr/local/lib/antlr-4.10.1-complete.jar'
        alias grun='java org.antlr.v4.gui.TestRig'
        
        source ~/.bashrc
        ```

      - Create conda env

        ```
        conda create -n scen python==3.7
        ```

      - Install antlr4 runtime and websocket

        ```
        pip install antlr4-python3-runtime==4.10
        pip3 install websocket
        pip3 install websocket-client
        ```

      - Install graphviz

        ```
        sudo apt-get install graphviz
        ```

      - Install python dependency

        ```
        pip install -r requirements.txt
        ```

        

   2. Prepare for judgement

      1. Create conda env

         ```
         conda create -n law python==3.7
         ```

      2. Install python dependency

         ```
         pip install -r requirements_judge.txt
         ```

         

## Quickstart

**1、Run carla**

```
./CarlaUE4.sh
```


**2、Run a OpenBehavior scenario**

```
conda activate scen

python scenario_runner.py --sync  --openscenario2 AVUnit_Osc/avunit_s1.osc --reloadWorld
```

**3、Run OSCFuzz**

```commandline
conda activate law

cd judgement

python OscFuzz.py
```


[contributors-shield]: https://img.shields.io/github/contributors/othneildrew/Best-README-Template.svg?style=for-the-badge
