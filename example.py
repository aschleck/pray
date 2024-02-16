import torch

print("hello")
print(f"cuda available: {torch.cuda.is_available()}")
print(f"device count: {torch.cuda.device_count()}")
print(f"device name: {torch.cuda.get_device_name(torch.cuda.current_device())}")
