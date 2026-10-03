import React, { Component } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { path } from '../utils/constant';

import ChatWorkspace from '../containers/Chat/ChatWorkspace';
import DocumentManager from '../containers/Documents/DocumentManager';
import SystemDashboard from '../containers/System/SystemDashboard';

class AppRoutes extends Component {
    render() {
        return (
            <Routes>
                {/* Main Feature Routes */}
                <Route path={path.HOME} element={<ChatWorkspace />} />
                <Route path={path.CHAT} element={<ChatWorkspace />} />
                <Route path={path.DOCUMENTS} element={<DocumentManager />} />
                <Route path={path.SYSTEM} element={<SystemDashboard />} />
                <Route path={path.DASHBOARD} element={<SystemDashboard />} />

                {/* Fallback to Home / Chat */}
                <Route path="*" element={<Navigate to={path.HOME} replace />} />
            </Routes>
        );
    }
}

export default AppRoutes;
