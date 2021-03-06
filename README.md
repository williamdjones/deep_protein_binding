# deep_protein_binding
## author: Derek Jones
repository for thesis project, learning molecular fingerprints for the classification of active versus decoy kinase binding interactions. The data
used for this project originates from the [DUD-E](dude.docking.org) database which is used to predict protein-small molecule interactions for the
purpose of developing computational methods for drug screening.

### Experiment 1
> In the first experiment, the goal is to learn a set of properties output by the [Dragon](https://chm.kode-solutions.net/products_dragon.php) chemoinformatics software suite. The purpose in doing this is 
to show that a data-driven approach can learn meaningful representations of the molecules from base representations (SMILES) in order 
    to eliminate the need for preprocessing requiring substantial domain expertise
    
### Experiment 2
> In the second experiment, the task is to use the molecular graphs of the molecules to predict binding affininity activity
classifaction.

All experiments make use of the [Hogwild!](https://papers.nips.cc/paper/5717-taming-the-wild-a-unified-analysis-of-hogwild-style-algorithms) distributed SGD algorithm.