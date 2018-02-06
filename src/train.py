import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-D', type=str, help="path to dataset")
parser.add_argument('-L', type=str, help="path to labels to use")
parser.add_argument("--n_workers", type=int, help="number of workers to use in data loader", default=0)
parser.add_argument("--batch_size", type=int, help="batch size to use in data loader", default=1)
parser.add_argument("--n_epochs", type=int, help="number of training epochs", default=1)
parser.add_argument("--use_cuda", type=bool, help="indicates whether to use gpu", default=False)
parser.add_argument("--lr", type=float, help="learning rate to use for training", default=1e-3)
parser.add_argument("--p", type=float, help="value for p in dropout layer", default=0.5)
parser.add_argument("--exp_name", type=str, help="name of the experiment", default="debug")

args = parser.parse_args()


if __name__ == "__main__":
    import torch.multiprocessing as multiprocessing
    # mp = mp.get_context("forkserver")
    # mp = mp.get_context("spawn")
    multiprocessing.set_start_method("forkserver")
    import os
    import torch
    import time
    from torch.utils.data.sampler import SubsetRandomSampler
    import numpy as np
    from MoleculeDataset import MoleculeDatasetH5, MoleculeDatasetCSV
    from torch.utils.data import DataLoader
    from sklearn.model_selection import train_test_split
    from tensorboardX import SummaryWriter
    from model import MPNN
    from utils import collate_fn, validation_step, train_step, update_scalars
    #TODO: implement cuda functionality, must convert model to cuda, convert input tensors and target, and criterion each to cuda
    #TODO: implement tensorboard functionality
    #TODO: implement multitask, use ModuleList object to hold (dynamically allocated) output layers for each task
    #TODO: use pinned memory for cuda?
    #TODO:implement random number generator seeds for numpy and pytorch
    # TODO: support using one copy of the model and loading it form disk before continuing to train

    print("{:=^100}".format(' Train '))




    # data = MoleculeDatasetH5(data_dir="/mounts/u-vul-d1/scratch/wdjo224/data/deep_protein_binding/datasets", list_dir="/mounts/u-vul-d1/scratch/wdjo224/data/deep_protein_binding/dataset_compounds",
    #                              corrupt_path="/u/vul-d1/scratch/wdjo224/data/deep_protein_binding/corrupt_inputs.csv",targets=["label"],num_workers=1)

    print("loading data...")
    target_list= ["Hy", "MLOGP", "vina_score"]
    molecules = MoleculeDatasetCSV(csv_file="/u/vul-d1/scratch/wdjo224/data/deep_protein_binding/kinase_no_duplicates_with_smiles.csv",
                              corrupt_path="/u/vul-d1/scratch/wdjo224/data/deep_protein_binding/corrupt_inputs.csv", targets=target_list, cuda=args.use_cuda)

    experiment_name = args.exp_name + "_" + str(time.time())
    epochs = args.n_epochs
    batch_size = args.batch_size
    num_workers = args.n_workers
    idxs = np.arange(0, len(molecules))

    train_idxs, val_idxs = train_test_split(idxs, stratify=molecules.activities.as_matrix().squeeze(), random_state=0)

    num_iters = int(np.ceil(train_idxs.shape[0] / batch_size))


    molecule_loader_train = DataLoader(molecules, batch_size=batch_size, num_workers=num_workers, collate_fn=collate_fn,
                                       sampler=SubsetRandomSampler(train_idxs))
    molecule_loader_val = DataLoader(molecules, batch_size=batch_size, num_workers=num_workers, collate_fn=collate_fn,
                                       sampler=SubsetRandomSampler(val_idxs))

    if args.use_cuda:
        molecule_loader_train = DataLoader(molecules, batch_size=batch_size, num_workers=num_workers,
                                           collate_fn=collate_fn, pin_memory=True, sampler=train_idxs)
        molecule_loader_val = DataLoader(molecules, batch_size=batch_size, num_workers=num_workers,
                                           collate_fn=collate_fn, pin_memory=True, sampler=val_idxs)
    print("train size: {} \t val size: {} \t batch size: {} \t learning rate: {} \t dropout p: {} \t num_iterations: {} \t "
          "num_workers: {} \t use_cuda: {}".format(train_idxs.shape[0], val_idxs.shape[0],batch_size, args.lr, args.p, num_iters, num_workers, args.use_cuda))

    print("instantiating model...")
    model = MPNN(T=3, p=args.p, n_tasks=len(target_list))
    print(model)
    if args.use_cuda:
        model.cuda()
    model.share_memory()

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    loss_fn = torch.nn.MSELoss()
    if args.use_cuda:
        loss_fn.cuda()

    print("initializing tensorboard writer...")
    # Create a writer for tensorboard
    if not os.path.exists("logs/"):
        os.makedirs("logs/")
    writer = SummaryWriter("logs/"+experiment_name)
    dummy_input = molecules[0]
    global_step = 0
    # writer.add_graph_onnx(model)
    # Train the model
    print("Training Model...")
    for epoch in range(0, epochs):

        for idx, batch in enumerate(molecule_loader_train):

            # zero the gradients for the next batch
            optimizer.zero_grad()

            # take a training step, i.e. process the mini-batch and accumulate gradients
            train_dict = train_step(model=model, batch=batch, target_list=target_list, loss_fn=loss_fn, use_cuda=args.use_cuda)

            print("epoch: {} \t step: {} \t train loss: {} \t train r2_score: {}".format(epoch, idx,
                                                                             train_dict["loss"],
                                                                             train_dict["r2"]))

            if idx % 10 == 0:
                # take a validation step for every 10 training steps
                val_dict = validation_step(model=model, batch=next(iter(molecule_loader_val)), loss_fn=loss_fn, target_list=target_list, use_cuda=args.use_cuda)
                print("\n epoch: {} \t step: {} \t val loss: {} \t val r2_score: {}".format(epoch, idx,
                                                                        val_dict["loss"],
                                                                        val_dict["r2"]))

            # update the model parameters
            optimizer.step()
            # log the information to tensorboard
            update_scalars(writer=writer, train_dict=train_dict, val_dict=val_dict, step=global_step)
            global_step += 1

    print("Finished training model")

    # Output training metrics
    print("Saving training metrics")
    scalar_path = "results/" + experiment_name + "_all_scalars.json"
    if not os.path.exists("results/"):
        os.makedirs("results/")

    writer.export_scalars_to_json(scalar_path)
    writer.close()

    print("Saving model weights...")
    if not os.path.exists("checkpoints/"):
        os.makedirs("checkpoints/")
    torch.save(model.state_dict(), "checkpoints/"+experiment_name)