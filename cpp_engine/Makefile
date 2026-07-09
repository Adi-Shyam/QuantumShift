# Makefile for C++ eBPF Scheduler

CLANG ?= clang
BPFTOOL ?= /usr/lib/linux-tools-6.8.0-134/bpftool
CXX ?= g++
CXXFLAGS := -g -O2 -Wall
INCLUDES := -I./src/common

all: sched_daemon

# Generate vmlinux.h from the running kernel
src/bpf/vmlinux.h:
	$(BPFTOOL) btf dump file /sys/kernel/btf/vmlinux format c > $@

# Compile BPF C code into object file
eqs.bpf.o: src/bpf/eqs.bpf.c src/common/eqs_types.h src/bpf/vmlinux.h
	$(CLANG) -g -O2 -target bpf -D__TARGET_ARCH_x86 -I./src/bpf $(INCLUDES) -c $< -o $@

# Generate BPF skeleton header
eqs.skel.h: eqs.bpf.o
	$(BPFTOOL) gen skeleton $< > $@

# Compile Simulator
simulator.o: src/daemon/simulator.cpp src/daemon/simulator.h
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Compile C++ Daemon
sched_daemon: src/daemon/sched_daemon.cpp eqs.skel.h simulator.o
	$(CXX) $(CXXFLAGS) $(INCLUDES) -I./libbpf/src -I. -o $@ src/daemon/sched_daemon.cpp simulator.o ./libbpf/src/libbpf.a -lelf -lz

clean:
	rm -f eqs.bpf.o eqs.skel.h simulator.o sched_daemon
