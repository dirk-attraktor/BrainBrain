ALL = brainfuck

FLAGS ?= -g -O3
CFLAGS ?= -g -O3
CXXFLAGS ?= -g -O3 
CPPFLAGS ?= -g -O3 

all: $(ALL)

clean:
	rm -rf $(ALL) *.o
