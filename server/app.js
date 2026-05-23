const express = require('express');
const fs =  require('fs');

const app = express();

app.use(express.json());

const TODO_FILE = 'todos.json';

function loadTodos() {
    try{
        const data = fs.readFileSync(TODO_FILE,'utf8');
        return JSON.parse(data);
    }
    catch(e)
    {
        return [];
    }
}
function saveTodos(todos)
{
    fs.writeFileSync(TODO_FILE,JSON.stringify(todos,null,4));
}

app.get('/todos',(req,res) => {
    res.json(todos);
});

let todos = loadTodos();

app.post('/todos',(req,res) => {
    todos.push(req.body);
    saveTodos(todos);
    res.json(todos);
});

app.put('/todos/:id/done',(req,res) => {
    const id = req.params.id;
    
    todos[id].done = true;
    saveTodos(todos);
    res.json(todos);
});

app.delete('/todos/:id',(req,res) => {
    const id = req.params.id;

    todos.splice(id,1);
    saveTodos(todos);
    res.json(todos);
});




app.listen(3000,() => {
    console.log('Server running on http://localhost:3000');
});