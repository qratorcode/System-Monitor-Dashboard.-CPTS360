#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_PROCESSES 100

/* 
   Process structure
    */
typedef struct {
    int pid;
    int arrival_time;
    int burst_time;

    /* Calculated / simulation fields */
    int remaining_time;
    int completion_time;
    int waiting_time;
    int turnaround_time;
} Process;

/* 
   Function Prototypes
    */
int  read_processes(const char *filename, Process processes[]);
void reset_processes(Process processes[], int n);
void sort_by_arrival(Process processes[], int n);

void fcfs(Process processes[], int n);
void sjf(Process processes[], int n);
void round_robin(Process processes[], int n, int quantum);

void print_metrics(Process processes[], int n);
void print_gantt(int pid, int start, int end);

/* 
   Main
    */
int main(int argc, char *argv[]) {
    Process processes[MAX_PROCESSES];
    int n;

    if (argc < 3) {
        printf("Usage: %s <input_file> <time_quantum>\n", argv[0]);
        return 1;
    }

    int quantum = atoi(argv[2]);

    n = read_processes(argv[1], processes);
    if (n <= 0) {
        printf("No processes loaded.\n");
        return 1;
    }

    /* Sort once by arrival time — all algorithms work on arrival-ordered data */
    sort_by_arrival(processes, n);

    printf("\n===== First-Come, First-Serve =====\n");
    reset_processes(processes, n);
    fcfs(processes, n);
    print_metrics(processes, n);

    printf("\n===== Shortest Job First =====\n");
    reset_processes(processes, n);
    sjf(processes, n);
    print_metrics(processes, n);

    printf("\n===== Round Robin (q = %d) =====\n", quantum);
    reset_processes(processes, n);
    round_robin(processes, n, quantum);
    print_metrics(processes, n);

    return 0;
}

/* 
   Read input file
   Each line: PID  Arrival_Time  Burst_Time
    */
int read_processes(const char *filename, Process processes[]) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        perror("Error opening file");
        return -1;
    }

    int count = 0;
    while (count < MAX_PROCESSES &&
           fscanf(fp, "%d %d %d",
                  &processes[count].pid,
                  &processes[count].arrival_time,
                  &processes[count].burst_time) == 3) {
        processes[count].remaining_time = processes[count].burst_time;
        count++;
    }

    fclose(fp);
    return count;
}

/* 
   Reset calculated fields for a fresh simulation run
    */
void reset_processes(Process processes[], int n) {
    for (int i = 0; i < n; i++) {
        processes[i].remaining_time  = processes[i].burst_time;
        processes[i].completion_time = 0;
        processes[i].waiting_time    = 0;
        processes[i].turnaround_time = 0;
    }
}

/* 
   Sort processes by arrival time (stable)
    */
void sort_by_arrival(Process processes[], int n) {
    for (int i = 1; i < n; i++) {
        Process key = processes[i];
        int j = i - 1;
        /* Strictly greater-than keeps equal-arrival entries in their
           original relative order (stable sort). */
        while (j >= 0 && processes[j].arrival_time > key.arrival_time) {
            processes[j + 1] = processes[j];
            j--;
        }
        processes[j + 1] = key;
    }
}

/* 
   First-Come, First-Serve scheduling
    */
void fcfs(Process processes[], int n) {
    int current_time = 0;

    for (int i = 0; i < n; i++) {
        /* CPU idle gap */
        if (current_time < processes[i].arrival_time)
            current_time = processes[i].arrival_time;

        int start = current_time;
        current_time += processes[i].burst_time;

        print_gantt(processes[i].pid, start, current_time);
        processes[i].completion_time = current_time;
    }
}

/*  
   Shortest Job First scheduling (non-preemptive)
    */
void sjf(Process processes[], int n) {
    int current_time = 0;
    int completed    = 0;
    int done[MAX_PROCESSES];
    memset(done, 0, sizeof(done));

    while (completed < n) {
        int best = -1;

        for (int i = 0; i < n; i++) {
            if (done[i] || processes[i].arrival_time > current_time)
                continue;

            if (best == -1
                || processes[i].burst_time < processes[best].burst_time
                || (processes[i].burst_time == processes[best].burst_time
                    && processes[i].arrival_time < processes[best].arrival_time)) {
                best = i;
            }
        }

        if (best == -1) {
            int next_arrival = -1;
            for (int i = 0; i < n; i++) {
                if (!done[i] && (next_arrival == -1
                                 || processes[i].arrival_time < next_arrival))
                    next_arrival = processes[i].arrival_time;
            }
            current_time = next_arrival;
        } else {
            int start = current_time;
            current_time += processes[best].burst_time;

            print_gantt(processes[best].pid, start, current_time);
            processes[best].completion_time = current_time;
            done[best] = 1;
            completed++;
        }
    }
}

/* 
   Round Robin scheduling
    */
void round_robin(Process processes[], int n, int quantum) {
    int current_time = 0;
    int completed    = 0;

    int queue[MAX_PROCESSES * MAX_PROCESSES];
    int front = 0, rear = 0;

    /* in_queue[i] = 1 while process i is sitting in the queue */
    int in_queue[MAX_PROCESSES];
    memset(in_queue, 0, sizeof(in_queue));

    for (int i = 0; i < n; i++) {
        if (processes[i].arrival_time <= current_time) {
            queue[rear++] = i;
            in_queue[i]   = 1;
        }
    }

    while (completed < n) {

        if (front == rear) {
            int next = -1;
            for (int i = 0; i < n; i++) {
                if (processes[i].remaining_time > 0
                    && (next == -1
                        || processes[i].arrival_time < next))
                    next = processes[i].arrival_time;
            }
            current_time = next;
            for (int i = 0; i < n; i++) {
                if (processes[i].arrival_time <= current_time
                    && processes[i].remaining_time > 0
                    && !in_queue[i]) {
                    queue[rear++] = i;
                    in_queue[i]   = 1;
                }
            }
        }

        int idx = queue[front++];
        in_queue[idx] = 0;

        int exec = (processes[idx].remaining_time < quantum)
                   ? processes[idx].remaining_time
                   : quantum;

        int start = current_time;
        current_time += exec;

        print_gantt(processes[idx].pid, start, current_time);
        processes[idx].remaining_time -= exec;

        for (int i = 0; i < n; i++) {
            if (i == idx) continue;
            if (processes[i].arrival_time <= current_time
                && processes[i].remaining_time > 0
                && !in_queue[i]) {
                queue[rear++] = i;
                in_queue[i]   = 1;
            }
        }

        if (processes[idx].remaining_time == 0) {
            processes[idx].completion_time = current_time;
            completed++;
        } else {
            queue[rear++] = idx;
            in_queue[idx] = 1;
        }
    }
}

/* 
   Print metrics table and averages
    */
void print_metrics(Process processes[], int n) {
    double total_wait       = 0.0;
    double total_turnaround = 0.0;

    printf("\nPID\tArrival\tBurst\tWaiting\tTurnaround\n");

    for (int i = 0; i < n; i++) {
        processes[i].turnaround_time =
            processes[i].completion_time - processes[i].arrival_time;
        processes[i].waiting_time =
            processes[i].turnaround_time - processes[i].burst_time;

        total_wait       += processes[i].waiting_time;
        total_turnaround += processes[i].turnaround_time;

        printf("%d\t%d\t%d\t%d\t%d\n",
               processes[i].pid,
               processes[i].arrival_time,
               processes[i].burst_time,
               processes[i].waiting_time,
               processes[i].turnaround_time);
    }

    printf("\nAverage Waiting Time: %.2f\n",    total_wait       / n);
    printf("Average Turnaround Time: %.2f\n",   total_turnaround / n);
}

/* 
   Print Gantt chart entry
    */
void print_gantt(int pid, int start, int end) {
    printf("P%d [%d -> %d]\n", pid, start, end);
}
