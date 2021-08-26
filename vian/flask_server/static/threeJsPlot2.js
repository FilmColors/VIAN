import * as THREE from '/static/three/build/three.module.js';
import Stats from '/static/three/jsm/libs/stats.module.js';
import { GUI } from '/static/three/jsm/libs/dat.gui.module.js';
import { DragControls } from '/static/three/jsm/controls/DragControls.js';
import { OrbitControls } from '/static/three/jsm/controls/OrbitControls.js';
import { TransformControls } from '/static/three/jsm/controls/TransformControls.js';
import { LineMaterial } from '/static/three/jsm/lines/LineMaterial.js';
import { LineGeometry } from '/static/three/jsm/lines/LineGeometry.js';
import { Line2 } from '/static/three/jsm/lines/Line2.js';

import { VRButton } from '/static/three/jsm/webxr/VRButton.js';
import { XRControllerModelFactory } from '/static/three/jsm/webxr/XRControllerModelFactory.js';

function rgb2ThreeColor(r, g, b) {
    return new THREE.Color("rgb(" + r + "," + g + "," + b + ")");
}
function floatRgb2ThreeColor(r, g, b) {
    let t = new THREE.Color()
    t.setRGB(r, g, b)
    return t
}

class ThreeJSView {
    constructor(frame_name, canvas_name, background_color = [17 / 255, 17 / 255, 17 / 255], useVr = false) {
        this.frame_name = frame_name;
        this.canvas_name = canvas_name;

        this.canvas = document.getElementById(canvas_name);
        this.frame = document.getElementById(frame_name);

        this.background_color = background_color
        const VERTEX_SCALE = 10;

        if (useVr == true && navigator.xr != null){
            this.useVr = true;
        }else{
            this.useVr = false;
        }

        this.scene = new THREE.Scene();
        this.renderWidth = this.frame.clientWidth;
        this.renderHeight = this.frame.clientHeight;
        if (this.fov == null) {
            this.fov = 75;
        }
        this.camera = new THREE.PerspectiveCamera(this.fov, this.renderWidth / this.renderHeight, 0.1, 1000);
        this.camera.updateProjectionMatrix();
        var currentCamera = this.camera;
        var ratio = this.renderHeight / this.renderWidth
        var orthoWidth = VERTEX_SCALE

        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
        this.scene.background = new THREE.Color("rgb(17,17,17)");
        this.renderer.setSize(this.renderWidth, this.renderHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.gammaInput = true;
        this.renderer.gammaOutput = true;
        this.renderer.shadowMap.enabled = false;
        this.renderer.xr.enabled = true;


        this.controls = new OrbitControls(this.camera, this.renderer.domElement);

        this.controls.damping = 0.5;
        this.controls.enableDamping = true; // an animation loop is required when either damping or auto-rotation are enabled
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.minDistance = 1;
        this.controls.maxDistance = 800;
        this.controls.enablePan = true;
        this.controls.minPolarAngle = -Math.PI;
        this.controls.maxPolarAngle = Math.PI;
        this.camera.position.set(0, 300, 0)
        this.initialTarget = this.controls.target;
        // this.controls.target.set(VERTEX_SCALE / 2, 0, 0);

        var targetObject = new THREE.Object3D();
        this.scene.add(targetObject);

        this.stats = new Stats();
        this.stats.showPanel(1);

        this.gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(this.gridHelper);

        // gridLines(this);
        if (this.useVr){
            this.initVrController();
        }
        var that = this;
        window.addEventListener('resize', function () { that.onWindowResize() }, false);
        this.frame.addEventListener('resize', function () { that.onWindowResize() }, false);

        this.frame.addEventListener("keydown", event => {
          if (event.keyCode === 70) {
            this.camera.position.set(0, 300, 0)
            this.controls.target.set(0,0,0)
          }
        });
        // window.addEventListener('mousemove', function (event) { onMouseMove(event) }, false);
        this.animate();
        // this.renderer.render(this.scene, this.camera);


    }

    handleController( controller ) {
        var pivot = controller.getObjectByName( 'pivot' );
        if ( pivot ) {
            var id = controller.userData.id;
            var matrix = pivot.matrixWorld;
            points[ id ].position.setFromMatrixPosition( matrix );
            // transformPoint( points[ id ].position );
            // if ( controller.userData.isSelecting ) {
            //     var strength = points[ id ].strength / 2;
            //     var vector = new THREE.Vector3().setFromMatrixPosition( matrix );
            //     transformPoint( vector );
            //     points.push( { position: vector, strength: strength, subtract: 10 } );

            // }
        }
    }

    animate() {
        var that = this;
        that.renderer.setAnimationLoop( function(){that.render(that); });
    }
    render(that) {
        if (this.useVr){
            this.handleController( that.controller1 );
            this.handleController( that.controller2 );
        }

        this.controls.update();
        this.renderer.render( that.scene, that.camera );
    }

    onWindowResize() {
        var frame = this.frame;
        var width = frame.clientWidth;
        var height = width;


        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    initVrController() {
        var that = this;
        document.body.appendChild(VRButton.createButton(this.renderer));

        // controllers

        // function onSelectStart() {
        //     this.userData.isSelecting = true;
        // }

        // function onSelectEnd() {

        //     this.userData.isSelecting = false;

        // }

        this.controller1 = this.renderer.xr.getController(0);

        // this.controller1.addEventListener('selectstart', onSelectStart);
        // this.controller1.addEventListener('selectend', onSelectEnd);

        this.controller1.addEventListener('connected', function (event) {
            this.add(buildController(event.data));
        });

        this.controller1.addEventListener('disconnected', function () {
            this.remove(this.children[0]);
        });

        this.scene.add(this.controller1);

        this.controller2 = this.renderer.xr.getController(1);

        // this.controller2.addEventListener('selectstart', onSelectStart);
        // this.controller2.addEventListener('selectend', onSelectEnd);

        this.controller2.addEventListener('connected', function (event) {
            this.add(buildController(event.data));
        });
        this.controller2.addEventListener('disconnected', function () {
            this.remove(this.children[0]);
        });

        this.scene.add(this.controller2);

        // The XRControllerModelFactory will automatically fetch controller models
        // that match what the user is holding as closely as possible. The models
        // should be attached to the object returned from getControllerGrip in
        // order to match the orientation of the held device.

        var controllerModelFactory = new XRControllerModelFactory();

        this.controllerGrip1 = this.renderer.xr.getControllerGrip(0);
        this.controllerGrip1.add(controllerModelFactory.createControllerModel(this.controllerGrip1));
        this.scene.add(this.controllerGrip1);

        this.controllerGrip2 = this.renderer.xr.getControllerGrip(1);
        this.controllerGrip2.add(controllerModelFactory.createControllerModel(this.controllerGrip2));
        this.scene.add(this.controllerGrip2);

        this.frame.appendChild(VRButton.createButton(this.renderer));

    }
    addPoint() {
        var sprite = new THREE.TextureLoader().load('/static/textures/disc.png');
        console.log(sprite)
        var geometry = new THREE.BufferGeometry();
        var vertices = [];
        for (var i = 0; i < 10000; i++) {

            var x = 100 * Math.random() - 50;
            var y = 100 * Math.random() - 50;
            var z = 100 * Math.random() - 50;

            vertices.push(x, y, z);

        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

        var material = new THREE.PointsMaterial({ size: 25, sizeAttenuation: false, map: sprite, alphaTest: 0.5, transparent: true });
        material.color.setHSL(1.0, 0.3, 0.7);

        var particles = new THREE.Points(geometry, material);
        this.scene.add(particles);
    }

    clear() {
        this.scene.remove.apply(this.scene, this.scene.children);
    }


}

class Palette3D extends ThreeJSView {
    constructor(rame_name, canvas_name, background_color = "rgb(255,255,255)") {
        super(rame_name, canvas_name, background_color)
        this._palette = []

        this._sprite = new THREE.TextureLoader().load('/static/textures/disc.png');

    }
    addPoint(l, a, b, col, size = 10) {
        let p = {}
        p.luminance = l;
        p.a = a;
        p.b = b;
        // p.col = rgb2ThreeColor(col[0], col[1], col[2])
        this._palette.push(p);

        let vertices = []
        vertices.push(a, l, b)

        var geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

        var material = new THREE.PointsMaterial({ size: size, sizeAttenuation: false, map: this._sprite, alphaTest: 0.5, transparent: true });
        material.color.setRGB(col[0], col[1], col[2]);

        var particles = new THREE.Points(geometry, material);
        this.scene.add(particles);
    }

    addPoints(ls, as, bs, cols, sizes){
        var ps = [];

        var vertices = []
        var colors = []
        for (var i = 0; i < ls.length; i ++){
            vertices.push(as[i], ls[i], bs[i])
            colors.push(cols[i][0], cols[i][1], cols[i][2], 0.5)
        }

        var geometry = new THREE.BufferGeometry();
        geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( vertices, 3 ) );
        geometry.setAttribute( 'color', new THREE.Float32BufferAttribute( colors, 4 ) );
        geometry.setAttribute( 'size', new THREE.Float32BufferAttribute( sizes, 1 ).setUsage( THREE.DynamicDrawUsage ) );

        var material = new THREE.PointsMaterial({ 
            size: 10, 
            sizeAttenuation: false, 
            map: this._sprite, 
            alphaTest: 0.5,
            transparent: true, 
            vertexColors:true });
        

        var particles = new THREE.Points(geometry, material);
        this.scene.add(particles);

    }

    clear() {
        this.scene.remove.apply(this.scene, this.scene.children);
        this._palette = []
    }
}

export {
    rgb2ThreeColor,

    ThreeJSView,
    Palette3D,

}