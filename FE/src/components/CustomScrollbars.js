import React, { Component } from 'react';
import { Scrollbars } from 'react-custom-scrollbars-2';
import './CustomScrollbars.scss';

class CustomScrollbars extends Component {
    ref = React.createRef();

    getScrollTop = () => {
        return this.ref.current ? this.ref.current.getScrollTop() : 0;
    };

    scrollToTop = () => {
        if (this.ref.current) {
            this.ref.current.scrollToTop();
        }
    };

    renderTrackHorizontal = (props) => {
        return <div {...props} className="track-horizontal" style={{ display: 'none' }} />;
    };

    renderTrackVertical = (props) => {
        return <div {...props} className="track-vertical" />;
    };

    renderThumbVertical = (props) => {
        return <div {...props} className="thumb-vertical" />;
    };

    render() {
        const { className, disableHorizontalScroll, children, ...otherProps } = this.props;
        return (
            <Scrollbars
                ref={this.ref}
                autoHide={true}
                autoHideTimeout={1000}
                autoHideDuration={200}
                renderTrackHorizontal={disableHorizontalScroll ? this.renderTrackHorizontal : undefined}
                renderTrackVertical={this.renderTrackVertical}
                renderThumbVertical={this.renderThumbVertical}
                className={className ? `${className} custom-scrollbar` : 'custom-scrollbar'}
                {...otherProps}
            >
                {children}
            </Scrollbars>
        );
    }
}

export default CustomScrollbars;
