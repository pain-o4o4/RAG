import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Navigate } from 'react-router-dom';
import { USER_ROLE } from '../utils/constant';

// 1. UserIsAuthenticated: For protected routes
class UserIsAuthenticatedComponent extends Component {
    render() {
        const { isLoggedIn, children } = this.props;
        return isLoggedIn ? children : <Navigate to="/login" replace />;
    }
}
const mapStateToPropsAuth = (state) => ({ isLoggedIn: state.user.isLoggedIn });
export const UserIsAuthenticated = connect(mapStateToPropsAuth)(UserIsAuthenticatedComponent);

// 2. UserIsNotAuthenticated: For guest routes like /login, /register
class UserIsNotAuthenticatedComponent extends Component {
    render() {
        const { isLoggedIn, children } = this.props;
        return !isLoggedIn ? children : <Navigate to="/" replace />;
    }
}
export const UserIsNotAuthenticated = connect(mapStateToPropsAuth)(UserIsNotAuthenticatedComponent);

// 3. UserIsAdmin: Requires roleId === R1 (Admin)
class UserIsAdminComponent extends Component {
    render() {
        const { isLoggedIn, userInfo, children } = this.props;
        const isAdmin = isLoggedIn && userInfo?.roleId === USER_ROLE.ADMIN;
        return isAdmin ? children : <Navigate to="/" replace />;
    }
}
const mapStateToPropsUser = (state) => ({
    isLoggedIn: state.user.isLoggedIn,
    userInfo: state.user.userInfo
});
export const UserIsAdmin = connect(mapStateToPropsUser)(UserIsAdminComponent);

// HOC Function Wrappers
export const userIsAuthenticated = (TargetComponent) => {
    return class extends Component {
        render() {
            return (
                <UserIsAuthenticated>
                    <TargetComponent {...this.props} />
                </UserIsAuthenticated>
            );
        }
    };
};

export const userIsNotAuthenticated = (TargetComponent) => {
    return class extends Component {
        render() {
            return (
                <UserIsNotAuthenticated>
                    <TargetComponent {...this.props} />
                </UserIsNotAuthenticated>
            );
        }
    };
};

export const userIsAdmin = (TargetComponent) => {
    return class extends Component {
        render() {
            return (
                <UserIsAdmin>
                    <TargetComponent {...this.props} />
                </UserIsAdmin>
            );
        }
    };
};
