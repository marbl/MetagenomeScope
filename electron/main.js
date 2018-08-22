/* Copyright (C) 2017-2018 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 ****
 * This code is run when the Electron app starts. It sets a callback that
 * starts a browser window of the MetagenomeScope viewer interface when the
 * app's ready.
 *
 * CODELINK: The bulk of this file's code is based on the tutorial located at
 * https://electronjs.org/docs/tutorial/first-app.
 */
const {app, BrowserWindow} = require('electron');

function createWindow() {
    win = new BrowserWindow({backgroundColor: '#fff', width: 1200, height: 900,
        autoHideMenuBar: true, icon: 'bubble_fancy.png'});
    win.loadFile('index.min.html');
}
app.on('ready', createWindow);
