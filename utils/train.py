import torch
import time
from utils.validate import validate
from torch.nn import functional as F
import torch.distributed as dist

def save_checkpoint(model, 
                    optimizer, 
                    epoch, 
                    filename="checkpoint/GPT2_TinyStory.pth"):
    # Save checkpoint only from rank 0
    if dist.get_rank() == 0:
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.module.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
        }
        torch.save(checkpoint, filename)
        print(f"Checkpoint saved at {filename}")

def train(model, 
          train_loader, 
          val_loader, 
          optimizer, 
          lr_scheduler,
          device, 
          num_epochs, 
          start_epoch, 
          save_step):
    model.train()
    start_time = time.time()

    for epoch in range(start_epoch, num_epochs):
        step = 0
        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()

            input_batch = input_batch.to(device)
            target_batch = target_batch.to(device)
            logits = model(input_batch)

            loss = F.cross_entropy(logits.flatten(0, 1), 
                                   target_batch.flatten())

            loss.backward()
            optimizer.step()

            # Print progress from rank 0 only
            if step % 10 == 0 and dist.get_rank() == 0:
                elapsed_time = time.time() - start_time
                print(f"Epoch {epoch}, Step {step}/{len(train_loader)}: Loss = {loss.item():.4f}, Time elapsed = {elapsed_time:.2f} sec")

            step += 1

            # Perform validation and save checkpoint at intervals
            if step % save_step == 0:
                if dist.get_rank() == 0:  # Only rank 0 will perform validation
                    validate(model, val_loader, device)

            # Update learning rate scheduler
            lr_scheduler.step()

            if step % save_step == 0:
                save_checkpoint(model, optimizer, epoch)