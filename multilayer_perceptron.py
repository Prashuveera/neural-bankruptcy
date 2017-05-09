import numpy as np
import tensorflow as tf

from algorithm import Algorithm


class MultilayerPerceptron(Algorithm):

    def __init__(self, n_input, n_hidden, num_epochs, batch_size, batch_iterator_type):
        # Structure of model
        self.n_input = n_input
        self.n_hidden = n_hidden
        self.n_class = 2
        # Training parameters
        self.num_epochs = num_epochs
        self.batch_size = batch_size
        self.batch_iterator_type = batch_iterator_type

        # Create TF graph and session
        tf.reset_default_graph()
        self.graph_nodes = self._get_graph()

        self.sess = tf.Session()
        self.sess.run([tf.global_variables_initializer()])
        # TODO: add early stopping with tf.train.Saver
        # TODO: add tf seed

    def fit(self, samples, labels):
        """Train the model with the samples and lables provided according to the parameters of the model."""

        if self.batch_iterator_type == 'normal':
            batch_iter = _batch_iter
        elif self.batch_iterator_type == 'oversample':
            batch_iter = _oversampling_batch_iter
        else:
            raise ValueError('{} is not a valid batch_iterator_type'.format(self.batch_iterator_type))

        for x, y in batch_iter(samples, labels, self.num_epochs, self.batch_size):
            # Train
            feed_dict = {
                    self.graph_nodes['x_input']: x,
                    self.graph_nodes['y_input']: y
                    }
            _, loss_val = self.sess.run([self.graph_nodes['optimize'], self.graph_nodes['loss']], feed_dict=feed_dict)
            # TODO: evaluate on dev set

    def predict_proba(self, samples):
        """Make probability predictions with the trained model."""
        feed_dict = {self.graph_nodes['x_input']: samples}  # Small model -> no need to loop over the samples
        proba = self.sess.run(self.graph_nodes['proba'], feed_dict=feed_dict)
        return proba

    def _get_graph(self):
        # Create placeholders for input
        x_input = tf.placeholder(tf.float32, shape=(None, self.n_input))
        y_input = tf.placeholder(tf.int32, shape=(None))

        # Variables
        # Build the fully connected layers
        # TODO: add dropout
        neurons = x_input
        for i in range(len(self.n_hidden) + 1):
            input_dim = self.n_input if i == 0 else self.n_hidden[i - 1]
            output_dim = self.n_class if i == len(self.n_hidden) else self.n_hidden[i]
            layer_name = i + 1 if i < len(self.n_hidden) else 'out'
            # Create weights
            W = tf.Variable(tf.truncated_normal([input_dim, output_dim], stddev=0.1),
                    name='W_{}_layer'.format(layer_name))
            b = tf.Variable(tf.truncated_normal([output_dim], stddev=0.1),
                    name='b_{}_layer'.format(layer_name))
            # Connect nodes
            neurons = tf.add(tf.matmul(neurons, W), b)
            if i < len(self.n_hidden):
                neurons = tf.nn.relu(neurons)  # TODO: make this optional

        logits = neurons
        proba = tf.nn.softmax(logits)

        # Loss and Accuracy
        loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y_input, logits=logits))
        correct_predictions = tf.equal(tf.cast(tf.argmax(logits, 1), tf.int32), y_input)
        accuracy = tf.reduce_mean(tf.cast(correct_predictions, 'float'))

        # Train operation
        # TODO: add so that we could change learning rate?
        optimize = tf.train.AdamOptimizer().minimize(loss)

        # Save important nodes to dict and return
        graph = {'x_input': x_input,
                'y_input': y_input,
                'proba': proba,
                'loss': loss,
                'accuracy': accuracy,
                'optimize': optimize}

        return graph


def _oversampling_batch_iter(samples, labels, num_epochs, batch_size):
    """Batch iterator that oversamples the rare class so that both classes become equally frequent."""
    pos_examples = (labels == 1)
    pos_samples, pos_labels = samples[pos_examples], labels[pos_examples]
    neg_examples = np.logical_not(pos_examples)
    neg_samples, neg_labels = samples[neg_examples], labels[neg_examples]

    neg_batch_size = np.floor(batch_size / 2)
    pos_batch_size = np.ceil(batch_size / 2)

    neg_batch_iter = _batch_iter(neg_samples, neg_labels, num_epochs, neg_batch_size)
    pos_batch_iter = _batch_iter(pos_samples, pos_labels, num_epochs, pos_batch_size)

    for neg_batch, pos_batch in zip(neg_batch_iter, pos_batch_iter):
        neg_batch_samples, neg_batch_labels = neg_batch
        pos_batch_samples, pos_batch_labels = pos_batch
        batch_samples = np.concatenate((neg_batch_samples, pos_batch_samples), axis=0)
        batch_labels = np.concatenate((neg_batch_labels, pos_batch_labels), axis=0)
        yield batch_samples, batch_labels


def _batch_iter(samples, labels, num_epochs, batch_size):
    """A batch iterator that generates batches from the data."""
    data_size = len(labels)
    n_batches_per_epoch = int(np.ceil(data_size / batch_size))
    for epoch in range(num_epochs):
        indices = np.arange(data_size)
        for batch_num in range(n_batches_per_epoch):
            start_index = int(batch_num * batch_size)
            end_index = int(min((batch_num + 1) * batch_size, data_size))
            yield samples[indices[start_index:end_index]], labels[indices[start_index:end_index]],
