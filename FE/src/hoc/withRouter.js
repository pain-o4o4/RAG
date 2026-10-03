import React from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';

export const withRouter = (Component) => {
    return function WithRouterComponent(props) {
        const location = useLocation();
        const navigate = useNavigate();
        const params = useParams();

        return (
            <Component
                {...props}
                navigate={navigate}
                location={location}
                params={params}
                router={{ location, navigate, params }}
            />
        );
    };
};

export default withRouter;
