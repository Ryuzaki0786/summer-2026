const http = require('http');

//const url = require('todos');

const todos = [
    { task: "Buy groceries", done: false },
    { task: "Solve LeetCode", done: true }
];

const server = http.createServer((req,res) => {
    if(req.url === '/todos' && req.method == 'POST')
    {
        let body = '';

        req.on('data',chunk => {
            body += chunk;
        });
        req.on('end',() => {
            const NewTodo = JSON.parse(body);
            todos.push(NewTodo);
            res.writeHead(200,{'content-type':'application/json'});
            res.end(JSON.stringify(todos));
            
        });
    }
    else if(req.url === '/todos' && req.method === 'GET')
    {
        res.writeHead(200,{'content-type':'application/json'});
        res.end(JSON.stringify(todos));
    }
    else{
        res.writeHead(404,{'content-type': 'text/plain'});
        res.end('Not Found');
    }
    console.log(req.url);

});

server.listen(3000,() => {
    console.log('Server running on http://localhost:3000');
});

