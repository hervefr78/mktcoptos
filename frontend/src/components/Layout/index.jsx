import React from 'react';
import Sidebar from './Sidebar';
import Breadcrumbs from './Breadcrumbs';
import { Outlet } from 'react-router-dom';
import './Layout.css';

const Layout = () => (
  <div className="app-layout">
    <Sidebar />
    <main className="main-content">
      <div className="content-wrapper">
        <Breadcrumbs />
        <div className="page-content">
          <Outlet />
        </div>
      </div>
    </main>
  </div>
);

export default Layout;
