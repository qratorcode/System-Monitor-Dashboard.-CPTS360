# PA3 – CPU Scheduling Simulator

Simulates FCFS, SJF (non-preemptive), and Round Robin CPU scheduling.

## Compile & Run

```bash
gcc -Wall scheduler.c -o scheduler
./scheduler <input_file> <time_quantum>
```

Example:
```bash
./scheduler processes.txt 2
```

## Input Format

One process per line: `PID  Arrival_Time  Burst_Time`

```
1 0 5
2 1 3
3 2 1
4 3 2
```

## Output

For each algorithm: a Gantt chart, per-process waiting and turnaround times, and averages.

## Assumptions

- Up to 100 processes
- SJF ties broken by earlier arrival time
- Time quantum must be a positive integer

## Sample Output

```
$ ./scheduler processes.txt 2

===== First-Come, First-Serve =====
P1 [0 -> 5]
P2 [5 -> 8]
P3 [8 -> 9]
P4 [9 -> 11]

PID     Arrival  Burst  Waiting  Turnaround
1       0        5      0        5
2       1        3      4        7
3       2        1      6        7
4       3        2      6        8

Average Waiting Time: 4.00
Average Turnaround Time: 6.75

===== Shortest Job First =====
P1 [0 -> 5]
P3 [5 -> 6]
P4 [6 -> 8]
P2 [8 -> 11]

PID     Arrival  Burst  Waiting  Turnaround
1       0        5      0        5
2       1        3      7        10
3       2        1      3        4
4       3        2      3        5

Average Waiting Time: 3.25
Average Turnaround Time: 6.00

===== Round Robin (q = 2) =====
P1 [0 -> 2]
P2 [2 -> 4]
P3 [4 -> 5]
P1 [5 -> 7]
P4 [7 -> 9]
P2 [9 -> 10]
P1 [10 -> 11]

PID     Arrival  Burst  Waiting  Turnaround
1       0        5      6        11
2       1        3      6        9
3       2        1      2        3
4       3        2      4        6

Average Waiting Time: 4.50
Average Turnaround Time: 7.25
```
