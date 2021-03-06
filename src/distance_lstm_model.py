import torch
import torch.nn as nn
import torch.autograd as autograd
import torch.optim as optim
from utils import *
from bilstm_model import BiLSTM_Model
from utils import _lengths_to_masks,_multi_bilayer_attention,target2distance



class DistAttLSTM_Model(nn.Module):

    def __init__(self,num_classes,max_length,num_tokens,embd,emb_dim = 300,hidden_dim=100,num_ways=3,lr=0.001):
        
        super(DistAttLSTM_Model,self).__init__()
        
        self.max_length = max_length
        
        self.num_tokens = num_tokens
        
        self.hidden_dim = hidden_dim
        
        self.num_classes = num_classes
        
        self.att_dim = 50
        
        self.depth = 10
        
        self.num_att = num_classes
        
        self.num_ways = num_ways
        
        self.lstm = BiLSTM_Model(max_length,num_tokens,embd,emb_dim,hidden_dim)
        
        self.linear = nn.Linear(self.hidden_dim*2, self.num_ways*self.num_classes)
        
        self.target_linear = nn.Linear(self.hidden_dim * 2,self.num_att * self.num_ways)
        
        self.target_linear_att = nn.Linear(self.hidden_dim * 2, 1)
    
        self.loss_fn = nn.functional.cross_entropy
        
        self.softmax = nn.Softmax()
        
        self.sigmoid = nn.Sigmoid()
        
        self.tanh = nn.Tanh()
        
        self.dropout = nn.Dropout(0.1)
        
        self.err = 1e-24
        
        self.optimizer = optim.Adam(filter(lambda p: p.requires_grad, self.parameters()), lr=lr)
    
    
    def target_attention_forward(self, lstm_outputs, targets):
                
        targets = target2distance(targets.data.numpy())
        
        target_outputs  = (targets.unsqueeze(2).expand_as(lstm_outputs) * lstm_outputs).sum(1)
        
        target_outputs =  target_outputs.squeeze(1)
                
        output_ = self.linear(target_outputs)
        
        output = self.dropout(output_.view(len(output_),-1,self.num_ways))
        
        output = self.softmax(output.view(-1,self.num_ways))
        
        return output,output_.view(-1,self.num_ways)
    
    def train_(self,x,y,targets,lengths):
        
        self.zero_grad()
        
        self.train()
        
        lstm_outputs = self.lstm.forward(x,lengths)
        
        output,output_ = self.target_attention_forward(lstm_outputs,targets)

        y = y.view(-1)
        
        loss = self.loss_fn(output_,y)
        
        loss.backward()
        
        self.optimizer.step()
        
        return loss
    
    
    def test(self,x,targets,lengths):
        
        self.eval()
        
        lstm_outputs = self.lstm.forward(x,lengths)
        
        output,output_ = self.target_attention_forward(lstm_outputs,targets)        
        
        return output.view(-1,self.num_classes,self.num_ways).data.numpy()