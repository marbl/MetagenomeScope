// CODELINK: https://electronjs.org/docs/tutorial/first-app
const {app, BrowserWindow} = require('electron');

function createWindow() {
    win = new BrowserWindow({backgroundColor: '#fff', width: 1200, height: 900,
        autoHideMenuBar: true, icon: 'bubble_fancy.png'});
    win.loadFile('index.min.html');
}
app.on('ready', createWindow);
