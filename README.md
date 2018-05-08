EthIR
=====


A framework for high-level Analysis of Ethereum Bytecode.

The tool extends [OYENTE framework](https://github.com/melonproject/oyente) to build the CFG of EVM programs analyzed and builds a Rule-based representation. This high-level representation can be injected in other resource static analayzers. 

## Installation
1. Install Solidity compiler (last version tested 0.4.19)
```
 sudo add-apt-repository ppa:ethereum/ethereum
 sudo apt-get update
 sudo apt-get install solc
```

2. Install Ethereum (last version tested 1.7.3)
```
 sudo apt-get install software-properties-common
 sudo add-apt-repository -y ppa:ethereum/ethereum
 sudo apt-get update
 sudo apt-get install ethereum
```

3. Install [Z3](https://github.com/Z3Prover/z3/releases) (last version tested 4.5.0)

   Download the [source code folder](https://github.com/Z3Prover/z3/releases/tag/z3-4.5.0).

   Decompress the folder and install it.
```
 unzip z3-z3-4.5.0.zip
 cd z3-z3-4.5.0
 python scripts/mk_make.py --python
 cd build
 make
 sudo make install
```
## Run EthIR

EthIR stores the RBR generated during its execution in the direcrtory /tmp/costabs/ .
To execute EthIR, run one of the following commands inside the folder *ethir*:

1. Run ETHIR from a solidity file:
```
./oyente-ethir -s solidity_file_name 
```
2. Run ETHIR from an EVM file:
```
./oyente-ethir -s evm_file_name -b 
```
3. Run ETHIR from a disassembly EVM file:
```
./oyente-ethir -s evmdisasm_file_name -disasm 
```
### Options
The command `./oyente-ethir -h` displays a list with all the available options of EthIR. Some of the most relevant ones are:

1. Store the control-flow-graph:
```
./oyente-ethir -s filename -cfg
```
2. Add nop annotations with EVM bytecodes:
```
./oyente-ethir -s filename -eop
```
3. Generate SACO RBR
```
./oyente-ethir -s filename -saco
```
## Examples
The folder *examples* contains running examples to test the tool.
Most of the examples such as bloccking.evm.disasm, advertisement.sol, validToken.sol or cryptoPhoenix.sol are real-world smart contracts obtained from the blockchain while others such as loop1.sol and sum.sol are ad-hoc examples where it is easier to undestand the decompilation process.

Note that some solidity files contain more than one smart contract and EthIR generates one RBR file per each one.

## Bounding Loops using SACO
[SACO](http://costa.fdi.ucm.es/saco/web/) is a static analyzer for concurrent objects which, is able to infer, among other properties,*upper bounds* on the number of iterations of loops. Note that this is the first crucial step to infer the gas
consumption of smart contracts.

The internal representation of [SACO](http://costa.fdi.ucm.es/saco/web/) matches the grammar of the RBR generated by EthIR after minor syntactic translations. Thanks to this, it is able to prove termination of the loops that some of the examples contain and produce a linear
bound for those loops. Here are some of the loop bounds inferred by SACO for some of the smart contracts contained in folder *examples*:

|Example|Bound|
|--|--|
| blockKing | nat(g8/10)*36+8934493 |
| cryptoPhoenix | nat(g3)*228409344+4113285485 |
| loop1 | nat(a)*25+234 |
| eligma | nat(_numberOfReturns)*2628+134 |
| lottery | 159 |
| blockSquareSerieA | 286 |
| validToken | inf |

Note that due to precision limitations of [SACO](http://costa.fdi.ucm.es/saco/web/) (it does not have bit-operations) the analyzer forgets the
information on bit variables. Due to this factor, [SACO](http://costa.fdi.ucm.es/saco/web/) is not able to infer a bound for some of the smart contracts.

Other high-level analyzers that work on intermediate forms like Integer transition systems or Horn clauses  (e.g., AproVe, T2, VeryMax, CoFloCo) could be easily adapted as well to work on RBR translated programs produced by EthIR. 

If you are interesting in using EthIR jointly with [SACO](http://costa.fdi.ucm.es/saco/web/) contact [SACO](http://costa.fdi.ucm.es/saco/web/) developers through a pull-request.
