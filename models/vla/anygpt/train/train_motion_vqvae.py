import os
import sys  
sys.path.append('SOLAMI/models/vla/anygpt/src/motiongpt')
os.environ["TRANSFORMERS_CACHE"] = "~/.cache/huggingface/hub"
import glob
import torch
import pytorch_lightning as pl
from omegaconf import OmegaConf
from mGPT.callback import build_callbacks
from mGPT.config import parse_args, instantiate_from_config
from mGPT.data.build_data import build_data
from mGPT.models.build_model import build_model
from mGPT.utils.logger import create_logger
from mGPT.utils.load_checkpoint import load_pretrained, load_pretrained_vae



def main():
    # Configs
    cfg = parse_args(phase="train")  # parse config file

    # Logger
    logger = create_logger(cfg, phase="train")  # create logger
    logger.info(OmegaConf.to_yaml(cfg))  # print config file

    # Seed
    pl.seed_everything(cfg.SEED_VALUE)

    # Environment Variables
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Metric Logger
    pl_loggers = []
    for loggerName in cfg.LOGGER.TYPE:
        if loggerName == 'tenosrboard' or cfg.LOGGER.WANDB.params.project:
            pl_logger = instantiate_from_config(
                eval(f'cfg.LOGGER.{loggerName.upper()}'))
            pl_loggers.append(pl_logger)

    # Callbacks
    callbacks = build_callbacks(cfg, logger=logger, phase='train')
    logger.info("Callbacks initialized")

    # Dataset
    datamodule = build_data(cfg)
    logger.info("datasets module {} initialized".format("".join(
        cfg.DATASET.target.split('.')[-2])))

    # Model
    model = build_model(cfg, datamodule)
    logger.info("model {} loaded".format(cfg.model.target))

    # Lightning Trainer
    trainer = pl.Trainer(
        default_root_dir=cfg.FOLDER_EXP,
        max_epochs=cfg.TRAIN.END_EPOCH,
        # precision='16',
        logger=pl_loggers,
        callbacks=callbacks,
        check_val_every_n_epoch=cfg.LOGGER.VAL_EVERY_STEPS,
        accelerator=cfg.ACCELERATOR,
        devices=cfg.DEVICE,
        num_nodes=cfg.NUM_NODES,
        strategy="ddp_find_unused_parameters_true"
        if len(cfg.DEVICE) > 1 else 'auto',
        benchmark=False,
        deterministic=False,
    )
    logger.info("Trainer initialized")


    def modified(model, cfg):
        if 'SPEECH_TOKENS' in cfg.TRAIN and cfg.TRAIN.SPEECH_TOKENS:
            if cfg.TRAIN.SPEECH_TOKENS == 'special':
                model.lm.add_speech_special_tokens()
            elif cfg.TRAIN.SPEECH_TOKENS == 'normal':
                model.lm.add_speech_normal_tokens()
            else:
                raise ValueError(f"Unknown speech token type: {cfg.TRAIN.SPEECH_TOKENS}")
        else:
            model.lm.add_none()

        if 'RIGHT_PADDING' in cfg.TRAIN and cfg.TRAIN.RIGHT_PADDING:
            model.lm.right_padding = True
        else:
            model.lm.right_padding = False
            
        if 'ONLY_ANSWER' in cfg.TRAIN and cfg.TRAIN.ONLY_ANSWER:
            model.lm.only_answer = True
        else:
            model.lm.only_answer = False


    if cfg.TRAIN.STAGE == 'lm_instruct' and cfg.TRAIN.TASK == 'interaction':
        if 'Pretrain' not in cfg.TRAIN.PRETRAINED:
            modified(model, cfg)

    # Strict load pretrianed model
    if cfg.TRAIN.PRETRAINED:
        load_pretrained(cfg, model, logger)

    # Strict load vae model
    if cfg.TRAIN.PRETRAINED_VAE:
        load_pretrained_vae(cfg, model, logger)
    
    if cfg.TRAIN.STAGE == 'lm_instruct' and cfg.TRAIN.TASK == 'interaction':
        if 'Pretrain' in cfg.TRAIN.PRETRAINED:
            modified(model, cfg)
    # Pytorch 2.0 Compile
    # if torch.__version__ >= "2.0.0":
    #     model = torch.compile(model, mode="reduce-overhead")
    # model = torch.compile(model)    

    # Lightning Fitting
    if cfg.TRAIN.RESUME:
        trainer.fit(model,
                    datamodule=datamodule,
                    ckpt_path=cfg.TRAIN.PRETRAINED)
    else:
        trainer.fit(model, datamodule=datamodule)

    # Training ends
    logger.info(
        f"The outputs of this experiment are stored in {cfg.FOLDER_EXP}")
    logger.info("Training ends!")


if __name__ == "__main__":
    main()
