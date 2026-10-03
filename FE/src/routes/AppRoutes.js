import React, { Component } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { path } from '../utils/constant';
import ChatWorkspace from '../containers/Chat/ChatWorkspace';

class AppRoutes extends Component {
    render() {
        return (
            <Routes>
                <Route path={path.HOME} element={<ChatWorkspace />} />
                <Route path={path.CHAT} element={<ChatWorkspace />} />
                <Route path="*" element={<Navigate to={path.HOME} replace />} />
            </Routes>
        );
    }
}

export default AppRoutes;
