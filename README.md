# OpenBehavior: A Behavior-Centric Scenario Description Language for Autonomous Driving Testing

<!-- PROJECT LOGO -->

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

### R2 Unable to reach the deatination

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
    <a href="sunshinesheep.github.io">View Details Demo</a>
  </p>

</div>

<!-- ABOUT THE PROJECT -->

## About The Project

This page presents multiple categories of bugs discovered in the Apollo autonomous driving system.

<!-- GETTING STARTED -->

## Getting Started

### Prerequisites

1. Install Carla(0.9.13)
   Download from https://github.com/carla-simulator/carla/releases.
2. Setup Apollo8.0
3. Setup Carla_apollo_bridge
4. Make Conda Env

## Quickstart

**1、Run carla**

```
./CarlaUE4.sh
```

**2、Start manual_control**

```
python manual_control.py -a --rolename=ego_vehicle
```

**3、Run a OpenBehavior scenario

```
python scenario_runner.py --sync  --openscenario2 AVUnit_Osc/avunit_s1.osc --reloadWorld

```


[contributors-shield]: https://img.shields.io/github/contributors/othneildrew/Best-README-Template.svg?style=for-the-badge
