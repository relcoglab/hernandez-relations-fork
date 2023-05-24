"""Run sweeps over different hyperparameters by relation."""
import argparse
import logging

from src import data, functional, hparams, models, sweeps
from src.utils import experiment_utils, logging_utils

import torch

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    logging_utils.configure(args)
    experiment = experiment_utils.setup_experiment(args)

    device = args.device or "cuda" if torch.cuda.is_available() else "cpu"

    dataset = data.load_dataset_from_args(args)
    mt = models.load_model(args.model, fp16=args.fp16, device=device)

    with torch.device(device):
        dataset = functional.filter_dataset_samples(mt=mt, dataset=dataset)
        results = sweeps.sweep(
            mt=mt,
            dataset=dataset,
            h_layers=args.h_layers,
            recall_k=args.recall_k,
            batch_size=args.batch_size,
            results_dir=experiment.results_dir,
            resume=args.resume,
        )
        for relation in results.relations:
            best_by_f = relation.best_by_faithfulness()
            best_by_e = relation.best_by_efficacy()
            hparams.RelationHParams(
                relation_name=relation.relation_name,
                h_layer=best_by_f.layer,
                h_layer_edit=best_by_e.layer,
                z_layer=-1,
                beta=best_by_f.beta.mean,
                # Not clear what this should be set to, if anything.
                # rank=math.floor(best_by_e.rank.mean),
                model_name=mt.name,
            ).save()

    results_file = experiment.results_dir / "results_all.json"
    results_file.parent.mkdir(exist_ok=True, parents=True)
    with results_file.open("w") as handle:
        handle.write(results.to_json(indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sweep over hyperparameters")
    data.add_data_args(parser)
    experiment_utils.add_experiment_args(parser)
    logging_utils.add_logging_args(parser)
    models.add_model_args(parser)
    parser.add_argument(
        "--h-layers", type=int, nargs="+", help="h layers to try, defaults to all"
    )
    parser.add_argument(
        "--recall-k",
        type=int,
        default=sweeps.DEFAULT_RECALL_K,
        help="compute up to recall@k",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=sweeps.DEFAULT_BATCH_SIZE,
        help="max batch size for lm",
    )
    args = parser.parse_args()
    main(args)
