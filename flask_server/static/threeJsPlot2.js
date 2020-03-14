import * as THREE from '/static/three/build/three.module.js';
import Stats from '/static/three/jsm/libs/stats.module.js';
import { GUI } from '/static/three/jsm/libs/dat.gui.module.js';
import { DragControls } from '/static/three/jsm/controls/DragControls.js';
import { OrbitControls } from '/static/three/jsm/controls/OrbitControls.js';
import { TransformControls } from '/static/three/jsm/controls/TransformControls.js';
import { LineMaterial } from '/static/three/jsm/lines/LineMaterial.js';
import { LineGeometry } from '/static/three/jsm/lines/LineGeometry.js';
import { Line2 } from '/static/three/jsm/lines/Line2.js';

function rgb2ThreeColor(r, g, b){
    return new THREE.Color("rgb(" + r + "," + g + "," + b + ")");
}
function floatRgb2ThreeColor(r, g, b){
    let t = new THREE.Color()
    t.setRGB(r, g, b)
    return t
}
class ThreeJSView{
    constructor(frame_name, canvas_name, background_color = [17/255,17/255,17/255]){
        this.frame_name = frame_name; 
        this.canvas_name = canvas_name; 
        
        this.canvas = document.getElementById(canvas_name);

        console.log(this.canvas)
        this.frame = document.getElementById(frame_name);
        
        this.background_color = background_color

        const VERTEX_SCALE = 10;

        this.scene = new THREE.Scene();
        this.renderWidth = this.frame.clientWidth;
        this.renderHeight = this.frame.clientHeight;
        if (this.fov == null){
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

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);

        this.controls.damping = 0.5;
        this.controls.enableDamping = true; // an animation loop is required when either damping or auto-rotation are enabled
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = true;
        this.controls.minDistance = 1;
        this.controls.maxDistance = 800;
        this.controls.enablePan = false;
        this.controls.maxPolarAngle = Math.PI / 2;
        this.camera.position.set(0,300,0)
        // this.controls.target.set(VERTEX_SCALE / 2, 0, 0);

        var targetObject = new THREE.Object3D();
        this.scene.add(targetObject);

        this.stats = new Stats();
        this.stats.showPanel(1);

        // this.frame.addEventListener("mousedown", function(){onClick()}, false);
        // this.frame.addEventListener("mouseup", function(){onRelease()}, false);
        // this.frame.addEventListener("onwheel", function(){onWheel()}, false);
        // this.canvas.onwheel = function(){onWheel(this)};

        this.gridHelper = new THREE.GridHelper(10, 10);
        this.scene.add(this.gridHelper);

        // gridLines(this);

        var that = this;
        window.addEventListener('resize', function () { that.onWindowResize() }, false);
        this.frame.addEventListener('resize', function () { that.onWindowResize() }, false);
        // window.addEventListener('mousemove', function (event) { onMouseMove(event) }, false);
        this.renderer.render(this.scene, this.camera);
    }

    animate(){
        var that = this;
        requestAnimationFrame(function () { that.animate() });
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        var frame = this.frame;
        var width = frame.clientWidth;
        var height = width;

    
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    addPoint(){
        var sprite = new THREE.TextureLoader().load( '/static/textures/disc.png' );
        console.log(sprite)
        var geometry = new THREE.BufferGeometry();
        var vertices = [];
        for ( var i = 0; i < 10000; i ++ ) {

            var x = 100 * Math.random() - 50;
            var y = 100 * Math.random() - 50;
            var z = 100 * Math.random() - 50;

            vertices.push( x, y, z );

        }

        geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( vertices, 3 ) );

        var material = new THREE.PointsMaterial( { size: 25, sizeAttenuation: false, map: sprite, alphaTest: 0.5, transparent: true } );
        material.color.setHSL( 1.0, 0.3, 0.7 );

        var particles = new THREE.Points( geometry, material );
        this.scene.add( particles );
    }

    clear(){
        this.scene.remove.apply(this.scene, this.scene.children);
    }


}

class Palette3D extends ThreeJSView{
    constructor(rame_name, canvas_name, background_color = "rgb(255,255,255)"){
        super(rame_name, canvas_name, background_color)
        this._palette = []

        this._sprite = new THREE.TextureLoader().load( '/static/textures/disc.png' );

    }
    addPoint(l, a, b, col, size=10){
        let p = {}
        p.luminance = l;
        p.a=a;
        p.b = b;
        // p.col = rgb2ThreeColor(col[0], col[1], col[2])
        this._palette.push(p);
        
        let vertices = []
        vertices.push(a, l, b)
        
        var geometry = new THREE.BufferGeometry();
        geometry.setAttribute( 'position', new THREE.Float32BufferAttribute( vertices, 3 ) );

        var material = new THREE.PointsMaterial( { size: size, sizeAttenuation: false, map: this._sprite, alphaTest: 0.5, transparent: true } );
        material.color.setRGB(col[0], col[1], col[2] );

        var particles = new THREE.Points( geometry, material );
        this.scene.add( particles );
    }
    clear(){
        this.scene.remove.apply(this.scene, this.scene.children);
        this._palette = []
    }
}

export{
    rgb2ThreeColor, 
    
    ThreeJSView,
    Palette3D, 
    
}